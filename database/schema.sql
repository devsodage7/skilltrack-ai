-- =====================================================================
--  SkillTrack AI  -  database/schema.sql
--  MySQL 8.0+  |  InnoDB  |  utf8mb4
--
--  WARNING: this script DROPs the 11 application tables and recreates
--  them. Run it once during setup, or use:
--      python database/init_db.py --reset
--
--  Table creation order respects foreign-key dependencies:
--    careers -> skills -> students -> career_skills -> student_skills
--    -> questions -> assessments -> quiz_results
--    -> learning_resources -> learning_progress -> resume_records
-- =====================================================================

CREATE DATABASE IF NOT EXISTS skilltrack_ai
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_general_ci;

USE skilltrack_ai;

SET NAMES utf8mb4;
SET time_zone = '+05:30';

-- Drop in reverse dependency order (safe even on a fresh database)
DROP TABLE IF EXISTS resume_records;
DROP TABLE IF EXISTS learning_progress;
DROP TABLE IF EXISTS learning_resources;
DROP TABLE IF EXISTS quiz_results;
DROP TABLE IF EXISTS assessments;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS student_skills;
DROP TABLE IF EXISTS career_skills;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS skills;
DROP TABLE IF EXISTS careers;

-- ---------------------------------------------------------------------
-- 1. careers  (reference data: the 8 career paths)
-- ---------------------------------------------------------------------
CREATE TABLE careers (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name        VARCHAR(80)  NOT NULL,
    slug        VARCHAR(80)  NOT NULL,
    description TEXT         NOT NULL,
    keywords    TEXT         NOT NULL,
    is_active   TINYINT(1)   NOT NULL DEFAULT 1,
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_careers_name (name),
    UNIQUE KEY uq_careers_slug (slug)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci;

-- ---------------------------------------------------------------------
-- 2. skills  (reference data: canonical skill names + categories)
-- ---------------------------------------------------------------------
CREATE TABLE skills (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name        VARCHAR(80)  NOT NULL,
    category    ENUM('programming','framework','database','tool','concept','soft')
                NOT NULL DEFAULT 'concept',
    description VARCHAR(255) NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_skills_name (name),
    KEY idx_skills_category (category)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci;

-- ---------------------------------------------------------------------
-- 3. students  (authentication + profile; role column gives admin access)
-- ---------------------------------------------------------------------
CREATE TABLE students (
    id             INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    full_name      VARCHAR(120)  NOT NULL,
    email          VARCHAR(160)  NOT NULL,
    password_hash  VARCHAR(255)  NOT NULL,
    role           ENUM('student','admin') NOT NULL DEFAULT 'student',
    phone          VARCHAR(20)   NULL,
    education      VARCHAR(120)  NULL,
    college        VARCHAR(160)  NULL,
    branch         VARCHAR(120)  NULL,
    year_of_study  TINYINT UNSIGNED NULL,
    career_goal_id INT UNSIGNED  NULL,
    interests      VARCHAR(255)  NULL,
    weekly_hours   TINYINT UNSIGNED NOT NULL DEFAULT 10,
    is_active      TINYINT(1)    NOT NULL DEFAULT 1,
    created_at     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                 ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_students_email (email),
    KEY idx_students_role (role),
    KEY idx_students_career_goal (career_goal_id),
    CONSTRAINT fk_students_career_goal
        FOREIGN KEY (career_goal_id) REFERENCES careers (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_students_year
        CHECK (year_of_study IS NULL OR (year_of_study BETWEEN 1 AND 5)),
    CONSTRAINT chk_students_hours
        CHECK (weekly_hours BETWEEN 1 AND 60)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci;

-- ---------------------------------------------------------------------
-- 4. career_skills  (requirement matrix: level, weight, prerequisite)
-- ---------------------------------------------------------------------
CREATE TABLE career_skills (
    id                    INT UNSIGNED NOT NULL AUTO_INCREMENT,
    career_id             INT UNSIGNED NOT NULL,
    skill_id              INT UNSIGNED NOT NULL,
    required_level        TINYINT UNSIGNED NOT NULL,
    weight                DECIMAL(3,2) NOT NULL,
    prerequisite_skill_id INT UNSIGNED NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_career_skill (career_id, skill_id),
    KEY idx_cs_skill (skill_id),
    KEY idx_cs_prereq (prerequisite_skill_id),
    CONSTRAINT fk_cs_career
        FOREIGN KEY (career_id) REFERENCES careers (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_cs_skill
        FOREIGN KEY (skill_id) REFERENCES skills (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_cs_prereq
        FOREIGN KEY (prerequisite_skill_id) REFERENCES skills (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_cs_required_level
        CHECK (required_level BETWEEN 1 AND 5),
    CONSTRAINT chk_cs_weight
        CHECK (weight > 0 AND weight <= 5)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci;

-- ---------------------------------------------------------------------
-- 5. student_skills  (the fused proficiency store - keeps all evidence)
-- ---------------------------------------------------------------------
CREATE TABLE student_skills (
    id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_id     INT UNSIGNED NOT NULL,
    skill_id       INT UNSIGNED NOT NULL,
    self_level     DECIMAL(3,1) NULL,
    resume_level   DECIMAL(3,1) NULL,
    quiz_level     DECIMAL(3,1) NULL,
    current_level  DECIMAL(3,1) NOT NULL DEFAULT 0.0,
    evidence_count SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    last_source    ENUM('self','resume','quiz','hybrid','none')
                   NOT NULL DEFAULT 'self',
    source_detail  JSON NULL,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_student_skill (student_id, skill_id),
    KEY idx_ss_skill (skill_id),
    KEY idx_ss_current (current_level),
    CONSTRAINT fk_ss_student
        FOREIGN KEY (student_id) REFERENCES students (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ss_skill
        FOREIGN KEY (skill_id) REFERENCES skills (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_ss_self
        CHECK (self_level IS NULL OR self_level BETWEEN 0 AND 5),
    CONSTRAINT chk_ss_resume
        CHECK (resume_level IS NULL OR resume_level BETWEEN 0 AND 5),
    CONSTRAINT chk_ss_quiz
        CHECK (quiz_level IS NULL OR quiz_level BETWEEN 0 AND 5),
    CONSTRAINT chk_ss_current
        CHECK (current_level BETWEEN 0 AND 5)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci;

-- ---------------------------------------------------------------------
-- 6. questions  (manual + template + Ollama generated bank)
-- ---------------------------------------------------------------------
CREATE TABLE questions (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
    skill_id        INT UNSIGNED NOT NULL,
    question_type   ENUM('mcq','output','coding','scenario') NOT NULL,
    difficulty      ENUM('beginner','intermediate','advanced') NOT NULL,
    question_text   TEXT NOT NULL,
    code_snippet    TEXT NULL,
    options         JSON NULL,
    correct_option  TINYINT UNSIGNED NULL,
    correct_answer  VARCHAR(255) NULL,
    explanation     TEXT NOT NULL,
    source          ENUM('manual','template','ollama') NOT NULL DEFAULT 'template',
    is_validated    TINYINT(1) NOT NULL DEFAULT 1,
    is_active       TINYINT(1) NOT NULL DEFAULT 1,
    created_by      INT UNSIGNED NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_q_skill_diff (skill_id, difficulty),
    KEY idx_q_type (question_type),
    KEY idx_q_source (source),
    KEY idx_q_active (is_active),
    CONSTRAINT fk_q_skill
        FOREIGN KEY (skill_id) REFERENCES skills (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_q_creator
        FOREIGN KEY (created_by) REFERENCES students (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_q_mcq
        CHECK (question_type <> 'mcq'
               OR (options IS NOT NULL
                   AND correct_option IS NOT NULL
                   AND correct_option BETWEEN 0 AND 3)),
    CONSTRAINT chk_q_explanation
        CHECK (CHAR_LENGTH(explanation) >= 10)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci;

-- ---------------------------------------------------------------------
-- 7. assessments  (one row per quiz attempt - header)
-- ---------------------------------------------------------------------
CREATE TABLE assessments (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_id      INT UNSIGNED NOT NULL,
    skill_id        INT UNSIGNED NULL,
    assessment_type ENUM('mcq','output','coding','scenario','mixed')
                    NOT NULL DEFAULT 'mcq',
    total_questions SMALLINT UNSIGNED NOT NULL,
    correct_answers SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    score_pct       DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    level_awarded   DECIMAL(3,1) NULL,
    duration_sec    INT UNSIGNED NULL,
    status          ENUM('in_progress','completed','abandoned')
                    NOT NULL DEFAULT 'in_progress',
    started_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at    TIMESTAMP NULL,
    PRIMARY KEY (id),
    KEY idx_as_student (student_id, started_at),
    KEY idx_as_skill (skill_id),
    KEY idx_as_status (status),
    CONSTRAINT fk_as_student
        FOREIGN KEY (student_id) REFERENCES students (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_as_skill
        FOREIGN KEY (skill_id) REFERENCES skills (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_as_score
        CHECK (score_pct BETWEEN 0 AND 100),
    CONSTRAINT chk_as_correct
        CHECK (correct_answers <= total_questions)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci;

-- ---------------------------------------------------------------------
-- 8. quiz_results  (one row per answered question)
-- ---------------------------------------------------------------------
CREATE TABLE quiz_results (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
    assessment_id   INT UNSIGNED NOT NULL,
    student_id      INT UNSIGNED NOT NULL,
    question_id     INT UNSIGNED NOT NULL,
    selected_option TINYINT UNSIGNED NULL,
    answer_text     TEXT NULL,
    is_correct      TINYINT(1) NOT NULL DEFAULT 0,
    time_taken_sec  SMALLINT UNSIGNED NULL,
    answered_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_qr_attempt_question (assessment_id, question_id),
    KEY idx_qr_student_question (student_id, question_id),
    KEY idx_qr_question (question_id),
    CONSTRAINT fk_qr_assessment
        FOREIGN KEY (assessment_id) REFERENCES assessments (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_qr_student
        FOREIGN KEY (student_id) REFERENCES students (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_qr_question
        FOREIGN KEY (question_id) REFERENCES questions (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_qr_option
        CHECK (selected_option IS NULL OR selected_option BETWEEN 0 AND 3)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci;

-- ---------------------------------------------------------------------
-- 9. learning_resources  (free resources only, stored locally)
-- ---------------------------------------------------------------------
CREATE TABLE learning_resources (
    id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
    skill_id      INT UNSIGNED NOT NULL,
    title         VARCHAR(200) NOT NULL,
    provider      VARCHAR(80)  NOT NULL,
    url           VARCHAR(500) NOT NULL,
    resource_type ENUM('video','docs','course','book','practice') NOT NULL,
    difficulty    ENUM('beginner','intermediate','advanced') NOT NULL,
    est_hours     DECIMAL(4,1) NOT NULL DEFAULT 6.0,
    is_free       TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    KEY idx_lr_skill_diff (skill_id, difficulty),
    CONSTRAINT fk_lr_skill
        FOREIGN KEY (skill_id) REFERENCES skills (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_lr_hours
        CHECK (est_hours > 0 AND est_hours <= 200)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci;

-- ---------------------------------------------------------------------
-- 10. learning_progress  (generated roadmap + student completion state)
-- ---------------------------------------------------------------------
CREATE TABLE learning_progress (
    id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_id   INT UNSIGNED NOT NULL,
    career_id    INT UNSIGNED NOT NULL,
    skill_id     INT UNSIGNED NOT NULL,
    resource_id  INT UNSIGNED NULL,
    topic_title  VARCHAR(200) NOT NULL,
    planned_hours DECIMAL(4,1) NOT NULL DEFAULT 6.0,
    week_number  TINYINT UNSIGNED NOT NULL,
    status       ENUM('pending','in_progress','completed')
                 NOT NULL DEFAULT 'pending',
    completed_at TIMESTAMP NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_lp_topic (student_id, career_id, skill_id, topic_title),
    KEY idx_lp_week (student_id, career_id, week_number),
    KEY idx_lp_skill (skill_id),
    KEY idx_lp_resource (resource_id),
    CONSTRAINT fk_lp_student
        FOREIGN KEY (student_id) REFERENCES students (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_lp_career
        FOREIGN KEY (career_id) REFERENCES careers (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_lp_skill
        FOREIGN KEY (skill_id) REFERENCES skills (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_lp_resource
        FOREIGN KEY (resource_id) REFERENCES learning_resources (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_lp_week
        CHECK (week_number BETWEEN 1 AND 52)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci;

-- ---------------------------------------------------------------------
-- 11. resume_records  (upload history + extraction output)
-- ---------------------------------------------------------------------
CREATE TABLE resume_records (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_id      INT UNSIGNED NOT NULL,
    career_id       INT UNSIGNED NULL,
    original_name   VARCHAR(255) NOT NULL,
    stored_name     VARCHAR(255) NOT NULL,
    file_size       INT UNSIGNED NOT NULL,
    file_hash       CHAR(64) NOT NULL,
    extracted_text  MEDIUMTEXT NULL,
    detected_skills JSON NULL,
    missing_skills  JSON NULL,
    match_score     DECIMAL(5,2) NULL,
    uploaded_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_rr_stored (stored_name),
    KEY idx_rr_student (student_id, uploaded_at),
    KEY idx_rr_career (career_id),
    CONSTRAINT fk_rr_student
        FOREIGN KEY (student_id) REFERENCES students (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_rr_career
        FOREIGN KEY (career_id) REFERENCES careers (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_rr_size
        CHECK (file_size > 0)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci;

-- =====================================================================
--  End of schema. Expected: 11 tables.
-- =====================================================================
