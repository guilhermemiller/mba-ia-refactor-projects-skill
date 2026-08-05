class HttpError extends Error {
    constructor(status, message) {
        super(message);
        this.name = 'HttpError';
        this.status = status;
    }
}

function asyncHandler(handler) {
    return (req, res, next) => Promise.resolve(handler(req, res, next)).catch(next);
}

function notFoundHandler(req, res) {
    res.status(404).json({ error: 'Rota não encontrada' });
}

function errorHandler(err, req, res, next) {
    if (res.headersSent) {
        console.error(`[ERROR] resposta já enviada em ${req.method} ${req.originalUrl}`, err);
        return next(err);
    }

    if (err instanceof HttpError) {
        return res.status(err.status).json({ error: err.message });
    }

    console.error(`[ERROR] ${req.method} ${req.originalUrl}`, err);
    return res.status(500).json({ error: 'Erro interno do servidor' });
}

module.exports = { HttpError, asyncHandler, notFoundHandler, errorHandler };
