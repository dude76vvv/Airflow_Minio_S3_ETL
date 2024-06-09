CREATE TABLE IF NOT EXISTS dest.pokedex (
    id int NOT NULL AUTO_INCREMENT,
    Pokedex_id INT NOT NULL,
    Name VARCHAR(100) NOT NULL,
    Type1 VARCHAR(20),
    Type2 VARCHAR(20),
    Hp INT,
    Attack INT,
    Defense INT,
    Speed INT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    constraint uc_pokeID_name unique(Pokedex_id,Name)
);