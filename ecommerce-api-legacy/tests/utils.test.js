const { config, logAndCache, badCrypto, globalCache, totalRevenue } = require('../src/utils');

describe('config', () => {
    it('exposes hardcoded credentials and the default port', () => {
        expect(config).toEqual({
            dbUser: 'admin_master',
            dbPass: 'senha_super_secreta_prod_123',
            paymentGatewayKey: 'pk_live_1234567890abcdef',
            smtpUser: 'no-reply@fullcycle.com.br',
            port: 3000
        });
    });

    it('is mutable shared state', () => {
        config.port = 4000;
        expect(require('../src/utils').config.port).toBe(4000);
        config.port = 3000;
    });
});

describe('logAndCache', () => {
    it('writes into the module-level cache and logs the key', () => {
        const log = jest.spyOn(console, 'log').mockImplementation(() => {});

        logAndCache('last_checkout_1', 'Clean Architecture');

        expect(globalCache.last_checkout_1).toBe('Clean Architecture');
        expect(log).toHaveBeenCalledWith('[LOG] Salvando no cache: last_checkout_1');
        log.mockRestore();
    });

    it('overwrites a previously cached value', () => {
        jest.spyOn(console, 'log').mockImplementation(() => {});

        logAndCache('key', 'first');
        logAndCache('key', 'second');

        expect(globalCache.key).toBe('second');
        console.log.mockRestore();
    });
});

describe('badCrypto', () => {
    it('returns a deterministic 10 character digest', () => {
        expect(badCrypto('123456')).toHaveLength(10);
        expect(badCrypto('123456')).toBe(badCrypto('123456'));
    });

    it('derives the digest from the base64 prefix of the password', () => {
        const prefix = Buffer.from('senha').toString('base64').substring(0, 2);

        expect(badCrypto('senha')).toBe(prefix.repeat(5));
    });

    it('collides for different passwords sharing a base64 prefix', () => {
        expect(badCrypto('senha1')).toBe(badCrypto('senha2'));
    });

    it('handles an empty password', () => {
        expect(badCrypto('')).toBe('');
    });
});

describe('totalRevenue', () => {
    it('is exported by value, so accumulating on it is lost', () => {
        expect(totalRevenue).toBe(0);
    });
});
