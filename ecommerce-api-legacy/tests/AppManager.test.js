const express = require('express');
const request = require('supertest');

const AppManager = require('../src/AppManager');

let manager;
let app;

const query = (sql, params = []) => new Promise((resolve, reject) => {
    manager.db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
});

const run = (sql, params = []) => new Promise((resolve, reject) => {
    manager.db.run(sql, params, (err) => (err ? reject(err) : resolve()));
});

const blockInsertsOn = (table) => run(
    `CREATE TRIGGER block_${table} BEFORE INSERT ON ${table} BEGIN SELECT RAISE(ABORT, 'blocked'); END`
);

beforeEach(async () => {
    jest.spyOn(console, 'log').mockImplementation(() => {});

    manager = new AppManager();
    manager.initDb();

    app = express();
    app.use(express.json());
    manager.setupRoutes(app);

    // initDb queues its statements, so wait until the seed data is visible.
    await query('SELECT * FROM courses');
});

afterEach(() => {
    console.log.mockRestore();
    manager.db.close();
});

const checkoutBody = (overrides = {}) => ({
    usr: 'Novo Aluno',
    eml: 'novo@fullcycle.com.br',
    pwd: 'segredo',
    c_id: 1,
    card: '4111111111111111',
    ...overrides
});

describe('constructor and initDb', () => {
    it('seeds users, courses, enrollments and payments in memory', async () => {
        expect(await query('SELECT * FROM users')).toHaveLength(1);
        expect(await query('SELECT * FROM courses')).toHaveLength(2);
        expect(await query('SELECT * FROM enrollments')).toHaveLength(1);
        expect(await query('SELECT * FROM payments')).toHaveLength(1);
    });
});

describe('POST /api/checkout', () => {
    it('creates the user, the enrollment and the payment for a new customer', async () => {
        const response = await request(app).post('/api/checkout').send(checkoutBody());

        expect(response.status).toBe(200);
        expect(response.body.msg).toBe('Sucesso');
        expect(response.body.enrollment_id).toBeDefined();

        const users = await query('SELECT * FROM users WHERE email = ?', ['novo@fullcycle.com.br']);
        expect(users).toHaveLength(1);
        expect(users[0].pass).toHaveLength(10);

        const payments = await query('SELECT * FROM payments WHERE enrollment_id = ?', [response.body.enrollment_id]);
        expect(payments[0]).toMatchObject({ amount: 997, status: 'PAID' });

        const logs = await query('SELECT * FROM audit_logs');
        expect(logs).toHaveLength(1);
    });

    it('reuses an existing user instead of creating a duplicate', async () => {
        const response = await request(app)
            .post('/api/checkout')
            .send(checkoutBody({ eml: 'leonan@fullcycle.com.br', usr: 'Leonan' }));

        expect(response.status).toBe(200);
        expect(await query('SELECT * FROM users')).toHaveLength(1);
        expect(await query('SELECT * FROM enrollments WHERE user_id = 1')).toHaveLength(2);
    });

    it('defaults the password of a new user when none is provided', async () => {
        const response = await request(app).post('/api/checkout').send(checkoutBody({ pwd: undefined }));

        expect(response.status).toBe(200);
        const users = await query('SELECT * FROM users WHERE email = ?', ['novo@fullcycle.com.br']);
        expect(users[0].pass).toHaveLength(10);
    });

    it('logs the raw card number and the payment gateway key', async () => {
        await request(app).post('/api/checkout').send(checkoutBody());

        expect(console.log).toHaveBeenCalledWith(
            expect.stringContaining('Processando cartão 4111111111111111 na chave pk_live_1234567890abcdef')
        );
    });

    it('rejects cards that do not start with 4 without enrolling', async () => {
        const response = await request(app).post('/api/checkout').send(checkoutBody({ card: '5111111111111111' }));

        expect(response.status).toBe(400);
        expect(response.text).toBe('Pagamento recusado');
        expect(await query('SELECT * FROM enrollments')).toHaveLength(1);
    });

    it.each([
        ['usr', { usr: undefined }],
        ['eml', { eml: undefined }],
        ['c_id', { c_id: undefined }],
        ['card', { card: undefined }]
    ])('returns 400 when %s is missing', async (_field, overrides) => {
        const response = await request(app).post('/api/checkout').send(checkoutBody(overrides));

        expect(response.status).toBe(400);
        expect(response.text).toBe('Bad Request');
    });

    it('returns 404 for an unknown course', async () => {
        const response = await request(app).post('/api/checkout').send(checkoutBody({ c_id: 999 }));

        expect(response.status).toBe(404);
        expect(response.text).toBe('Curso não encontrado');
    });

    it('returns 404 for an inactive course', async () => {
        await run('UPDATE courses SET active = 0 WHERE id = 1');

        const response = await request(app).post('/api/checkout').send(checkoutBody());

        expect(response.status).toBe(404);
    });

    it('returns 500 when the user lookup fails', async () => {
        await run('DROP TABLE users');

        const response = await request(app).post('/api/checkout').send(checkoutBody());

        expect(response.status).toBe(500);
        expect(response.text).toBe('Erro DB');
    });

    it('returns 500 when creating the user fails', async () => {
        await blockInsertsOn('users');

        const response = await request(app).post('/api/checkout').send(checkoutBody());

        expect(response.status).toBe(500);
        expect(response.text).toBe('Erro ao criar usuário');
    });

    it('returns 500 when creating the enrollment fails', async () => {
        await blockInsertsOn('enrollments');

        const response = await request(app).post('/api/checkout').send(checkoutBody());

        expect(response.status).toBe(500);
        expect(response.text).toBe('Erro Matrícula');
    });

    it('returns 500 when registering the payment fails', async () => {
        await blockInsertsOn('payments');

        const response = await request(app).post('/api/checkout').send(checkoutBody());

        expect(response.status).toBe(500);
        expect(response.text).toBe('Erro Pagamento');
    });
});

describe('GET /api/admin/financial-report', () => {
    it('aggregates paid revenue and students per course', async () => {
        const response = await request(app).get('/api/admin/financial-report');

        expect(response.status).toBe(200);
        const byCourse = Object.fromEntries(response.body.map((entry) => [entry.course, entry]));

        expect(byCourse['Clean Architecture']).toEqual({
            course: 'Clean Architecture',
            revenue: 997,
            students: [{ student: 'Leonan', paid: 997 }]
        });
        expect(byCourse.Docker).toEqual({ course: 'Docker', revenue: 0, students: [] });
    });

    it('sums the revenue of every enrollment of a course', async () => {
        await run("INSERT INTO users (name, email, pass) VALUES ('Ana', 'ana@fullcycle.com.br', 'x')");
        await run('INSERT INTO enrollments (user_id, course_id) VALUES (2, 1)');
        await run("INSERT INTO payments (enrollment_id, amount, status) VALUES (2, 500.00, 'PAID')");

        const response = await request(app).get('/api/admin/financial-report');

        const cleanArch = response.body.find((entry) => entry.course === 'Clean Architecture');
        expect(cleanArch.revenue).toBe(1497);
        expect(cleanArch.students).toEqual(
            expect.arrayContaining([
                { student: 'Leonan', paid: 997 },
                { student: 'Ana', paid: 500 }
            ])
        );
    });

    it('ignores unpaid payments when summing revenue', async () => {
        await run("UPDATE payments SET status = 'DENIED' WHERE enrollment_id = 1");

        const response = await request(app).get('/api/admin/financial-report');

        const cleanArch = response.body.find((entry) => entry.course === 'Clean Architecture');
        expect(cleanArch.revenue).toBe(0);
        expect(cleanArch.students).toEqual([{ student: 'Leonan', paid: 997 }]);
    });

    it('reports zero paid for enrollments without a payment row', async () => {
        await run('DELETE FROM payments');

        const response = await request(app).get('/api/admin/financial-report');

        const cleanArch = response.body.find((entry) => entry.course === 'Clean Architecture');
        expect(cleanArch).toEqual({
            course: 'Clean Architecture',
            revenue: 0,
            students: [{ student: 'Leonan', paid: 0 }]
        });
    });

    it('returns an empty report when there are no courses', async () => {
        await run('DELETE FROM courses');

        const response = await request(app).get('/api/admin/financial-report');

        expect(response.status).toBe(200);
        expect(response.body).toEqual([]);
    });

    it('lists every course with zero revenue when there are no enrollments', async () => {
        await run('DELETE FROM enrollments');

        const response = await request(app).get('/api/admin/financial-report');

        expect(response.status).toBe(200);
        expect(response.body).toEqual([
            { course: 'Clean Architecture', revenue: 0, students: [] },
            { course: 'Docker', revenue: 0, students: [] }
        ]);
    });

    it('returns 500 when the courses query fails', async () => {
        await run('DROP TABLE courses');

        const response = await request(app).get('/api/admin/financial-report');

        expect(response.status).toBe(500);
        expect(response.text).toBe('Erro DB');
    });

    it('reports unknown students for enrollments whose user was deleted', async () => {
        await request(app).delete('/api/users/1');

        const response = await request(app).get('/api/admin/financial-report');

        const cleanArch = response.body.find((entry) => entry.course === 'Clean Architecture');
        expect(cleanArch.students).toEqual([{ student: 'Unknown', paid: 997 }]);
    });
});

describe('DELETE /api/users/:id', () => {
    it('deletes the user but leaves enrollments and payments orphaned', async () => {
        const response = await request(app).delete('/api/users/1');

        expect(response.status).toBe(200);
        expect(response.text).toBe('Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.');
        expect(await query('SELECT * FROM users WHERE id = 1')).toHaveLength(0);
        expect(await query('SELECT * FROM enrollments WHERE user_id = 1')).toHaveLength(1);
        expect(await query('SELECT * FROM payments')).toHaveLength(1);
    });

    it('answers with success even for an unknown user', async () => {
        const response = await request(app).delete('/api/users/999');

        expect(response.status).toBe(200);
    });
});
