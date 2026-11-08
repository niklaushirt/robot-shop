//
// Users
//
// Seed passwords are supplied through environment variables so that no
// credentials are stored in source control.
//
function seedPassword(name) {
    var value;
    if(typeof process !== 'undefined' && process.env) {
        // mongosh
        value = process.env[name];
    } else if(typeof getenv === 'function') {
        // legacy mongo shell
        value = getenv(name);
    } else if(typeof _getEnv === 'function') {
        value = _getEnv(name);
    }
    if(!value) {
        throw new Error('missing required environment variable ' + name);
    }
    return value;
}

db = db.getSiblingDB('users');
db.users.insertMany([
    {name: 'user', password: seedPassword('USER_SEED_PASSWORD'), email: 'user@me.com'},
    {name: 'stan', password: seedPassword('STAN_SEED_PASSWORD'), email: 'stan@instana.com'},
    {name: 'partner-57', password: seedPassword('PARTNER_SEED_PASSWORD'), email: 'howdy@partner.com'}
]);

// unique index on the name
db.users.createIndex(
    {name: 1},
    {unique: true}
);

