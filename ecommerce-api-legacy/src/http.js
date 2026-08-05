/** Utilitários compartilhados de resposta HTTP. */

class HttpError extends Error {
    constructor(status, message) {
        super(message);
        this.status = status;
    }
}

/** Converte a falha de uma promise em um HttpError com mensagem própria. */
function orFail(promise, status, message) {
    return promise.then(
        (value) => value,
        () => {
            throw new HttpError(status, message);
        }
    );
}

/** Envolve um handler async, traduzindo HttpError em resposta de erro. */
function asyncRoute(handler) {
    return (req, res) => {
        Promise.resolve(handler(req, res)).catch((err) => {
            const status = err instanceof HttpError ? err.status : 500;
            res.status(status).send(err.message || 'Erro interno');
        });
    };
}

module.exports = { HttpError, orFail, asyncRoute };
