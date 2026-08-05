const sqlite3 = require('sqlite3').verbose();
const { config, logAndCache, badCrypto, totalRevenue } = require('./utils');
const { HttpError, asyncHandler } = require('./errorHandler');

class AppManager {
    constructor() {

        this.db = new sqlite3.Database(':memory:');
    }

    run(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.run(sql, params, function (err) {
                if (err) return reject(err);
                resolve({ lastID: this.lastID, changes: this.changes });
            });
        });
    }

    get(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
        });
    }

    all(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
        });
    }

    async initDb() {
        await this.run("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT)");
        await this.run("CREATE TABLE courses (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER)");
        await this.run("CREATE TABLE enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER)");
        await this.run("CREATE TABLE payments (id INTEGER PRIMARY KEY, enrollment_id INTEGER, amount REAL, status TEXT)");
        await this.run("CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME)");

        await this.run("INSERT INTO users (name, email, pass) VALUES ('Leonan', 'leonan@fullcycle.com.br', '123')");
        await this.run("INSERT INTO courses (title, price, active) VALUES ('Clean Architecture', 997.00, 1), ('Docker', 497.00, 1)");
        await this.run("INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)");
        await this.run("INSERT INTO payments (enrollment_id, amount, status) VALUES (1, 997.00, 'PAID')");
    }

    setupRoutes(app) {
        app.post('/api/checkout', asyncHandler(async (req, res) => {
            let u = req.body.usr;
            let e = req.body.eml;
            let p = req.body.pwd;
            let cid = req.body.c_id;
            let cc = req.body.card;

            if (!u || !e || !cid || !cc) throw new HttpError(400, 'Bad Request');

            const course = await this.get("SELECT * FROM courses WHERE id = ? AND active = 1", [cid]);
            if (!course) throw new HttpError(404, 'Curso não encontrado');

            const user = await this.get("SELECT id FROM users WHERE email = ?", [e]);

            let userId;
            if (user) {
                userId = user.id;
            } else {
                let hash = badCrypto(p || "123456");
                const created = await this.run("INSERT INTO users (name, email, pass) VALUES (?, ?, ?)", [u, e, hash]);
                userId = created.lastID;
            }

            console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
            let status = cc.startsWith("4") ? "PAID" : "DENIED";

            if (status === "DENIED") throw new HttpError(400, 'Pagamento recusado');

            const enrollment = await this.run("INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)", [userId, cid]);
            let enrId = enrollment.lastID;

            await this.run("INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)", [enrId, course.price, status]);
            await this.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [`Checkout curso ${cid} por ${userId}`]);

            logAndCache(`last_checkout_${userId}`, course.title);
            res.status(200).json({ msg: "Sucesso", enrollment_id: enrId });
        }));

        app.get('/api/admin/financial-report', asyncHandler(async (req, res) => {
            const courses = await this.all("SELECT * FROM courses", []);
            const report = [];

            for (const c of courses) {
                const courseData = { course: c.title, revenue: 0, students: [] };
                const enrollments = await this.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id]);

                for (const enr of enrollments) {
                    const user = await this.get("SELECT name, email FROM users WHERE id = ?", [enr.user_id]);
                    const payment = await this.get("SELECT amount, status FROM payments WHERE enrollment_id = ?", [enr.id]);

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

        app.delete('/api/users/:id', asyncHandler(async (req, res) => {
            let id = req.params.id;
            const result = await this.run("DELETE FROM users WHERE id = ?", [id]);

            if (result.changes === 0) throw new HttpError(404, 'Usuário não encontrado');

            res.json({ msg: "Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco." });
        }));
    }
}

module.exports = AppManager;
