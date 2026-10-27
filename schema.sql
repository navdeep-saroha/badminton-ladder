-- Badminton Ladder schema.
-- Rebuilds the tables from scratch: psql ladder -f schema.sql
-- WARNING: drops existing tables and all their data.

-- challenges references players, so it must be dropped first.
DROP TABLE IF EXISTS challenges;
DROP TABLE IF EXISTS players;

CREATE TABLE players (
    id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username TEXT    NOT NULL UNIQUE CHECK (username ~ '^[a-z0-9_.]{3,20}$'),
    name     TEXT    NOT NULL CHECK (char_length(name) BETWEEN 1 AND 50),
    rank     INTEGER NOT NULL UNIQUE CHECK (rank >= 1)
);

CREATE TABLE challenges (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    challenger_id BIGINT NOT NULL REFERENCES players (id),
    defender_id   BIGINT NOT NULL REFERENCES players (id),
    status        TEXT   NOT NULL DEFAULT 'OPEN'
                  CHECK (status IN ('OPEN', 'COMPLETED', 'EXPIRED', 'CANCELLED')),
    CHECK (challenger_id <> defender_id)
);
