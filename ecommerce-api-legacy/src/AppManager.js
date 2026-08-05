const sqlite3 = require('sqlite3').verbose();
const { config, logAndCache, badCrypto, totalRevenue } = require('./utils');
const { dbGet, dbAll, dbRun } = require('./db');
const { HttpError, orFail, asyncRoute } = require('./http');

const SCHEMA = [
    "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT)",
    "CREATE TABLE courses (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER)",
    "CREATE TABLE enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER)",
    "CREATE TABLE payments (id INTEGER PRIMARY KEY, enrollment_id INTEGER, amount REAL, status TEXT)",
    "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME)"
];

const SEED = [
    "INSERT INTO users (name, email, pass) VALUES ('Leonan', 'leonan@fullcycle.com.br', '123')",
    "INSERT INTO courses (title, price, active) VALUES ('Clean Architecture', 997.00, 1), ('Docker', 497.00, 1)",
    "INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)",
    "INSERT INTO payments (enrollment_id, amount, status) VALUES (1, 997.00, 'PAID')"
];

class AppManager {
    constructor() {

        this.db = new sqlite3.Database(':memory:');
    }

    initDb() {
        this.db.serialize(() => {
            SCHEMA.concat(SEED).forEach((sql) => this.db.run(sql));
        });
    }

    setupRoutes(app) {
        app.post('/api/checkout', asyncRoute(async (req, res) => {
            let u = req.body.usr;
            let e = req.body.eml;
            let p = req.body.pwd;
            let cid = req.body.c_id;
            let cc = req.body.card;

            if (!u || !e || !cid || !cc) return res.status(400).send("Bad Request");

            const course = await dbGet(this.db, "SELECT * FROM courses WHERE id = ? AND active = 1", [cid])
                .catch(() => null);
            if (!course) throw new HttpError(404, "Curso não encontrado");

            const user = await orFail(
                dbGet(this.db, "SELECT id FROM users WHERE email = ?", [e]),
                500, "Erro DB"
            );

            let userId;
            if (!user) {

                let hash = badCrypto(p || "123456");
                userId = await orFail(
                    dbRun(this.db, "INSERT INTO users (name, email, pass) VALUES (?, ?, ?)", [u, e, hash]),
                    500, "Erro ao criar usuário"
                );
            } else {
                userId = user.id;
            }

            console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
            let status = cc.startsWith("4") ? "PAID" : "DENIED";

            if (status === "DENIED") return res.status(400).send("Pagamento recusado");

            const enrId = await orFail(
                dbRun(this.db, "INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)", [userId, cid]),
                500, "Erro Matrícula"
            );

            await orFail(
                dbRun(this.db, "INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)",
                    [enrId, course.price, status]),
                500, "Erro Pagamento"
            );

            await dbRun(this.db, "INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))",
                [`Checkout curso ${cid} por ${userId}`]).catch(() => null);

            logAndCache(`last_checkout_${userId}`, course.title);
            res.status(200).json({ msg: "Sucesso", enrollment_id: enrId });
        }));

        app.get('/api/admin/financial-report', asyncRoute(async (req, res) => {
            const courses = await orFail(dbAll(this.db, "SELECT * FROM courses"), 500, "Erro DB");

            const report = [];
            for (const c of courses) {
                const courseData = { course: c.title, revenue: 0, students: [] };
                const enrollments = await dbAll(this.db, "SELECT * FROM enrollments WHERE course_id = ?", [c.id]);

                for (const enr of enrollments) {
                    const user = await dbGet(this.db, "SELECT name, email FROM users WHERE id = ?", [enr.user_id]);
                    const payment = await dbGet(this.db, "SELECT amount, status FROM payments WHERE enrollment_id = ?", [enr.id]);

                    if (payment && payment.status === 'PAID') {
                        courseData.revenue += payment.amount;
                    }

                    courseData.students.push({
                        student: user ? user.name : 'Unknown',
                        paid: payment ? payment.amount : 0
                    });
                }

                report.push(courseData);
            }

            res.json(report);
        }));

        app.delete('/api/users/:id', asyncRoute(async (req, res) => {
            await dbRun(this.db, "DELETE FROM users WHERE id = ?", [req.params.id]).catch(() => null);
            res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.");
        }));
    }
}

module.exports = AppManager;
