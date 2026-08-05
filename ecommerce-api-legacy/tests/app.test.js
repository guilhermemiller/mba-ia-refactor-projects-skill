const express = require('express');
const request = require('supertest');

const { config } = require('../src/utils');

let app;
let log;
let listen;

beforeAll(() => {
    log = jest.spyOn(console, 'log').mockImplementation(() => {});

    // app.js binds a port on import; capture the instance instead of listening.
    listen = jest.spyOn(express.application, 'listen').mockImplementation(function mockListen(port, callback) {
        app = this;
        if (callback) callback();
        return { close: jest.fn() };
    });

    require('../src/app');
});

afterAll(() => {
    listen.mockRestore();
    log.mockRestore();
});

it('starts the server on the configured port', () => {
    expect(listen).toHaveBeenCalledWith(config.port, expect.any(Function));
    expect(log).toHaveBeenCalledWith(`Frankenstein LMS rodando na porta ${config.port}...`);
});

it('wires the AppManager routes into the express app', () => {
    const routes = app._router.stack
        .filter((layer) => layer.route)
        .map((layer) => `${Object.keys(layer.route.methods)[0].toUpperCase()} ${layer.route.path}`);

    expect(routes).toEqual([
        'POST /api/checkout',
        'GET /api/admin/financial-report',
        'DELETE /api/users/:id'
    ]);
});

it('serves the seeded financial report through the composed app', async () => {
    const response = await request(app).get('/api/admin/financial-report');

    expect(response.status).toBe(200);
    expect(response.body).toEqual(
        expect.arrayContaining([
            { course: 'Clean Architecture', revenue: 997, students: [{ student: 'Leonan', paid: 997 }] }
        ])
    );
});

it('parses JSON bodies, so a checkout without fields is rejected as bad request', async () => {
    const response = await request(app).post('/api/checkout').send({});

    expect(response.status).toBe(400);
    expect(response.text).toBe('Bad Request');
});
