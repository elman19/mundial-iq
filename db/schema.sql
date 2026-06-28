--PostgreSQLSchema

 -- =============================================================
-- Mundial IQ | PostgreSQL Schema
-- World Cup 2026 AI Analytics Engine
-- =============================================================

-- 1. GROUPS
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    name CHAR(1) NOT NULL UNIQUE,         -- e.g., 'A', 'B', ..., 'L'
    round VARCHAR(50) DEFAULT 'Group Stage',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_groups_name ON groups(name);


-- 2. TEAMS
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    code VARCHAR(3) NOT NULL UNIQUE,       -- e.g., 'ARG', 'FRA', 'BRA'
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    flag_url TEXT,
    group_id INT REFERENCES groups(id) ON DELETE RESTRICT,
    fifa_ranking INT CHECK (fifa_ranking > 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_teams_code ON teams(code);
CREATE INDEX idx_teams_group_id ON teams(group_id);


-- 3. STADIUMS
CREATE TABLE stadiums (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    country VARCHAR(100) NOT NULL,
    capacity INT CHECK (capacity > 0),
    timezone VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_stadiums_city ON stadiums(city);


-- 4. PLAYERS
CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    team_id INT NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(150) NOT NULL,
    birth_date DATE,
    jersey_number INT CHECK (jersey_number BETWEEN 1 AND 99),
    position VARCHAR(20) CHECK (position IN ('Goalkeeper', 'Defender', 'Midfielder', 'Forward')),
    is_captain BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_players_team ON players(team_id);
CREATE INDEX idx_players_position ON players(position);
CREATE INDEX idx_players_last_name ON players(last_name);


-- 5. GAMES
CREATE TABLE games (
    _id SERIAL PRIMARY KEY,
    id VARCHAR(50) NOT NULL UNIQUE,
    public_match_id INT CHECK (public_match_id BETWEEN 1 AND 104),
    home_team_id INT NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    away_team_id INT NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    stadium_id INT REFERENCES stadiums(id) ON DELETE SET NULL,
    home_score INT DEFAULT 0 CHECK (home_score >= 0),
    away_score INT DEFAULT 0 CHECK (away_score >= 0),
    time_elapsed INT DEFAULT 0 CHECK (time_elapsed >= 0),
    "group" VARCHAR(10),
    matchday INT,
    type VARCHAR(50),
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    local_date VARCHAR(50),
    finished BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_games_id ON games(id);
CREATE INDEX idx_games_teams ON games(home_team_id, away_team_id);
CREATE INDEX idx_games_date ON games(date);


-- 6. MATCH EVENTS
CREATE TABLE match_events (
    id SERIAL PRIMARY KEY,
    game_id INT NOT NULL REFERENCES games(_id) ON DELETE CASCADE,
    team_id INT NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    type VARCHAR(30) NOT NULL CHECK (type IN (
        'Goal', 'Own Goal', 'Penalty Goal', 'Penalty Miss',
        'Yellow Card', 'Second Yellow Card', 'Red Card',
        'Substitution', 'Injury Time'
    )),
    minute INT NOT NULL CHECK (minute >= 0),
    extra_minute INT DEFAULT 0 CHECK (extra_minute >= 0),
    primary_player_id INT REFERENCES players(id) ON DELETE RESTRICT,
    secondary_player_id INT REFERENCES players(id) ON DELETE RESTRICT,
    details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_match_events_game ON match_events(game_id);
CREATE INDEX idx_match_events_type ON match_events(type);