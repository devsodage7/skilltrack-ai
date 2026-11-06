-- =====================================================================
--  SkillTrack AI  -  database/seed_career_skills.sql
--  68 rows = the weighted requirement matrix (A4) and the prerequisite
--  DAG (A6). Weight per career sums to 1.00.
--
--  Columns: career_id, skill_id, required_level (1-5), weight, prerequisite_skill_id
--  prerequisite_skill_id references skills.id (or NULL when none).
-- =====================================================================

USE skilltrack_ai;

INSERT IGNORE INTO career_skills
    (career_id, skill_id, required_level, weight, prerequisite_skill_id) VALUES

-- 1. Python Developer  (sum = 1.00)
(1,  1, 5, 0.30, NULL),   -- Python
(1,  6, 3, 0.15, NULL),   -- SQL
(1, 16, 3, 0.10, NULL),   -- Git
(1, 13, 4, 0.15,    1),   -- Flask          <- Python
(1, 15, 4, 0.12,   13),   -- REST API       <- Flask
(1, 20, 4, 0.08,    1),   -- Unit Testing   <- Python
(1, 19, 3, 0.05, NULL),   -- Linux
(1, 18, 3, 0.05, NULL),   -- Docker

-- 2. Data Analyst  (sum = 1.00)
(2,  6, 5, 0.25, NULL),   -- SQL
(2, 22, 4, 0.16,    1),   -- Pandas         <- Python
(2, 27, 4, 0.15, NULL),   -- Statistics
(2, 24, 4, 0.12, NULL),   -- Excel
(2,  1, 3, 0.12, NULL),   -- Python
(2, 28, 4, 0.10,    6),   -- Data Cleaning  <- SQL
(2, 29, 4, 0.06,   28),   -- Data Viz       <- Data Cleaning
(2, 25, 3, 0.04,   29),   -- Power BI       <- Data Viz

-- 3. Data Scientist  (sum = 1.00)
(3, 31, 5, 0.20,   27),   -- Machine Learning   <- Statistics
(3, 27, 5, 0.18, NULL),   -- Statistics
(3,  1, 5, 0.15, NULL),   -- Python
(3, 22, 4, 0.12,    1),   -- Pandas             <- Python
(3, 33, 4, 0.12,   31),   -- Scikit-learn       <- Machine Learning
(3,  6, 4, 0.10, NULL),   -- SQL
(3, 29, 4, 0.08,   28),   -- Data Viz           <- Data Cleaning
(3, 39, 4, 0.05,   31),   -- Feature Engineering<- Machine Learning

-- 4. Machine Learning Engineer  (sum = 1.00)
(4,  1, 5, 0.18, NULL),   -- Python
(4, 31, 5, 0.18,   27),   -- Machine Learning   <- Statistics
(4, 32, 4, 0.14,   31),   -- Deep Learning      <- Machine Learning
(4, 34, 4, 0.10,   32),   -- TensorFlow         <- Deep Learning
(4, 35, 4, 0.10,   32),   -- PyTorch            <- Deep Learning
(4, 40, 4, 0.10,   18),   -- MLOps              <- Docker
(4, 18, 4, 0.09, NULL),   -- Docker
(4, 16, 4, 0.06, NULL),   -- Git
(4, 19, 3, 0.05, NULL),   -- Linux

-- 5. AI Engineer  (sum = 1.00)
(5,  1, 5, 0.18, NULL),   -- Python
(5, 31, 5, 0.16,   27),   -- Machine Learning   <- Statistics
(5, 32, 4, 0.14,   31),   -- Deep Learning      <- Machine Learning
(5, 36, 4, 0.14,   32),   -- NLP                <- Deep Learning
(5, 35, 4, 0.10,   32),   -- PyTorch            <- Deep Learning
(5, 37, 3, 0.10,   32),   -- Computer Vision    <- Deep Learning
(5, 15, 3, 0.08,   13),   -- REST API           <- Flask
(5, 18, 3, 0.06, NULL),   -- Docker
(5, 19, 3, 0.04, NULL),   -- Linux

-- 6. Web Developer  (sum = 1.00)
(6,  9, 5, 0.22, NULL),   -- HTML/CSS
(6,  4, 5, 0.22, NULL),   -- JavaScript
(6, 11, 4, 0.12,    4),   -- React              <- JavaScript
(6, 15, 3, 0.10,    4),   -- REST API           <- JavaScript
(6,  6, 3, 0.10, NULL),   -- SQL
(6, 10, 3, 0.08,    9),   -- Bootstrap          <- HTML/CSS
(6, 16, 3, 0.08, NULL),   -- Git
(6, 47, 2, 0.08,    9),   -- Web Security       <- HTML/CSS

-- 7. Full Stack Developer  (sum = 1.00)
(7,  4, 5, 0.15, NULL),   -- JavaScript
(7,  9, 5, 0.13, NULL),   -- HTML/CSS
(7, 11, 4, 0.13,    4),   -- React              <- JavaScript
(7, 12, 4, 0.13,    4),   -- Node.js            <- JavaScript
(7, 15, 4, 0.12,   12),   -- REST API           <- Node.js
(7, 41, 4, 0.11,    6),   -- MySQL              <- SQL
(7, 16, 4, 0.08, NULL),   -- Git
(7, 18, 3, 0.06, NULL),   -- Docker
(7, 47, 3, 0.05,    9),   -- Web Security       <- HTML/CSS
(7, 10, 3, 0.04,    9),   -- Bootstrap          <- HTML/CSS

-- 8. Cybersecurity Analyst  (sum = 1.00)
(8, 45, 4, 0.22, NULL),   -- Networking
(8, 19, 4, 0.18, NULL),   -- Linux
(8, 47, 4, 0.15,   45),   -- Web Security       <- Networking
(8, 48, 4, 0.12,   45),   -- SIEM Tools         <- Networking
(8, 46, 3, 0.12,   45),   -- Cryptography       <- Networking
(8,  1, 3, 0.10, NULL),   -- Python
(8, 50, 4, 0.08,   48),   -- Incident Response  <- SIEM Tools
(8, 49, 3, 0.03,   47);   -- Penetration Testing<- Web Security
