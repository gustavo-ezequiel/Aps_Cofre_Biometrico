-- Banco do Cofre Biometrico (MySQL / XAMPP)
-- Opcional: o programa cria tudo sozinho ao iniciar com DB_ENGINE = "mysql".
-- Use este script se quiser criar pelo phpMyAdmin (http://localhost/phpmyadmin).

CREATE DATABASE IF NOT EXISTS cofre_biometrico
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE cofre_biometrico;

CREATE TABLE IF NOT EXISTS usuarios (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  nome       VARCHAR(100) NOT NULL,
  cargo      VARCHAR(100),
  nivel      TINYINT NOT NULL,              -- 1 geral, 2 diretor, 3 ministro
  ativo      TINYINT NOT NULL DEFAULT 1,
  criado_em  DATETIME NOT NULL,
  CHECK (nivel BETWEEN 1 AND 3)
);

CREATE TABLE IF NOT EXISTS acessos (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id  INT NULL,                     -- NULL = rosto desconhecido
  nivel_area  TINYINT NOT NULL,             -- area que tentou acessar
  resultado   VARCHAR(20) NOT NULL,         -- CONCEDIDO / NEGADO / BLOQUEIO
  motivo      VARCHAR(255),
  distancia   DOUBLE,                       -- distancia LBPH (menor = mais parecido)
  foto        VARCHAR(255),                 -- foto do intruso, se negado
  data_hora   DATETIME NOT NULL,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Consultas uteis para o relatorio/dissertacao
-- Tentativas por resultado:
--   SELECT resultado, COUNT(*) FROM acessos GROUP BY resultado;
-- Negacoes por area:
--   SELECT nivel_area, COUNT(*) FROM acessos WHERE resultado='NEGADO' GROUP BY nivel_area;

-- ================================================================
-- CONTEUDO DO COFRE: uma tabela por nivel de seguranca
-- (o programa recria estas tabelas a partir de dados_cofre.py ao iniciar)
-- ================================================================

DROP TABLE IF EXISTS nivel1_registro_toxinas;
DROP TABLE IF EXISTS nivel2_relatorios_incidentes;
DROP TABLE IF EXISTS nivel3_arquivos_ultrassecretos;

-- NIVEL 1 - Baixa periculosidade ambiental
DROP TABLE IF EXISTS nivel1_baixa_periculosidade;
CREATE TABLE nivel1_baixa_periculosidade (
  id INT AUTO_INCREMENT PRIMARY KEY,
  substancia VARCHAR(80),
  onde_encontrada VARCHAR(120),
  risco_ambiental VARCHAR(150)
);
INSERT INTO nivel1_baixa_periculosidade (substancia, onde_encontrada, risco_ambiental) VALUES
  ('Bicarbonato de sódio', 'Produtos domésticos', 'Baixo em pequenas quantidades'),
  ('Ácido cítrico', 'Alimentos e produtos de limpeza', 'Baixo em soluções diluídas'),
  ('Etanol diluído', 'Produtos de limpeza', 'Pode afetar organismos em altas concentrações'),
  ('Cloreto de sódio', 'Sal de cozinha', 'Pode salinizar o solo e a água'),
  ('Carbonato de cálcio', 'Rochas e produtos industriais', 'Geralmente baixo');

-- NIVEL 2 - Periculosidade moderada a elevada
DROP TABLE IF EXISTS nivel2_periculosidade_moderada;
CREATE TABLE nivel2_periculosidade_moderada (
  id INT AUTO_INCREMENT PRIMARY KEY,
  substancia VARCHAR(80),
  onde_encontrada VARCHAR(120),
  risco_ambiental VARCHAR(150)
);
INSERT INTO nivel2_periculosidade_moderada (substancia, onde_encontrada, risco_ambiental) VALUES
  ('Hipoclorito de sódio', 'Desinfetantes', 'Tóxico para organismos aquáticos'),
  ('Amônia', 'Fertilizantes e indústrias', 'Pode causar mortalidade de peixes'),
  ('Sulfato de cobre', 'Agricultura e indústria', 'Tóxico para organismos aquáticos'),
  ('Formaldeído', 'Indústrias e laboratórios', 'Tóxico e prejudicial à saúde'),
  ('Tolueno', 'Solventes e tintas', 'Pode contaminar o ar, a água e o solo');

-- NIVEL 3 - Periculosidade ambiental extrema
DROP TABLE IF EXISTS nivel3_periculosidade_extrema;
CREATE TABLE nivel3_periculosidade_extrema (
  id INT AUTO_INCREMENT PRIMARY KEY,
  substancia VARCHAR(80),
  perigo_ambiental VARCHAR(150),
  controle VARCHAR(150)
);
INSERT INTO nivel3_periculosidade_extrema (substancia, perigo_ambiental, controle) VALUES
  ('Dioxinas (ex.: TCDD)', 'Persistência, bioacumulação e toxicidade elevada', 'Controle rigoroso de emissões e resíduos'),
  ('Bifenilas policloradas (PCBs)', 'Contaminação persistente de solos e águas', 'Restrições internacionais'),
  ('Metilmercúrio', 'Bioacumulação em peixes e cadeias alimentares', 'Controle de emissões e exposição'),
  ('Tributilestanho (TBT)', 'Toxicidade elevada para organismos marinhos', 'Restrições severas de uso');
