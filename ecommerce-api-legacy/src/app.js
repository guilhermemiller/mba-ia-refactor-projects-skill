const express = require('express');
const AppManager = require('./AppManager');
const { config } = require('./utils');
const { notFoundHandler, errorHandler } = require('./errorHandler');

const app = express();
app.use(express.json());

const manager = new AppManager();

async function start() {
    await manager.initDb();
    manager.setupRoutes(app);

    app.use(notFoundHandler);
    app.use(errorHandler);

    app.listen(config.port, () => {
        console.log(`Frankenstein LMS rodando na porta ${config.port}...`);
    });
}

process.on('unhandledRejection', (reason) => {
    console.error('[FATAL] unhandledRejection', reason);
    process.exit(1);
});

start().catch((err) => {
    console.error('[FATAL] falha ao inicializar a aplicação', err);
    process.exit(1);
});
