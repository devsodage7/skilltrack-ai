-- =====================================================================
--  SkillTrack AI  -  database/seed_demo_activity.sql
--  Demo quiz history so charts, trends, admin analytics and K-Means
--  clustering have data on day one. All rows are internally consistent:
--  correct_answers <= total_questions and is_correct matches the option
--  recorded in seed_questions.sql.
--
--  Answers are graded exactly as quiz_service does:
--    MCQ        -> selected_option == correct_option
--    output/etc -> keyword / normalised text match against correct_answer
-- =====================================================================

USE skilltrack_ai;

-- ---------------------------------------------------------------------
-- Assessment headers
-- ---------------------------------------------------------------------
INSERT IGNORE INTO assessments
    (id, student_id, skill_id, assessment_type, total_questions,
     correct_answers, score_pct, level_awarded, duration_sec, status,
     started_at, completed_at)
VALUES
(1, 2,  1, 'mcq', 5, 3, 60.00, 3.0, 420, 'completed', '2026-10-20 10:00:00', '2026-10-20 10:07:00'),
(2, 2, 31, 'mcq', 5, 2, 40.00, 2.0, 510, 'completed', '2026-10-24 17:30:00', '2026-10-24 17:38:30'),
(3, 4,  1, 'mcq', 5, 4, 80.00, 4.0, 360, 'completed', '2026-10-22 09:15:00', '2026-10-22 09:21:00'),
(4, 7,  9, 'mcq', 4, 3, 75.00, 4.0, 300, 'completed', '2026-10-25 14:00:00', '2026-10-25 14:05:00'),
(5, 9, 47, 'mcq', 4, 3, 75.00, 4.0, 330, 'completed', '2026-10-27 19:00:00', '2026-10-27 19:05:30'),
(6, 3,  6, 'mcq', 5, 4, 80.00, 4.0, 390, 'completed', '2026-10-28 11:00:00', '2026-10-28 11:06:30'),
(7, 2,  1, 'mcq', 5, 4, 80.00, 4.0, 355, 'completed', '2026-11-02 20:00:00', '2026-11-02 20:05:55');

-- ---------------------------------------------------------------------
-- Answer level rows
-- ---------------------------------------------------------------------
INSERT IGNORE INTO quiz_results
    (assessment_id, student_id, question_id, selected_option, answer_text,
     is_correct, time_taken_sec, answered_at)
VALUES
-- Assessment 1: Aarav, Python, 3 of 5
(1, 2,  1, 0,    NULL,   1, 55, '2026-10-20 10:01:00'),
(1, 2,  2, 1,    NULL,   0, 80, '2026-10-20 10:02:20'),
(1, 2,  3, NULL, '3',    1, 95, '2026-10-20 10:03:55'),
(1, 2,  4, 1,    NULL,   0, 90, '2026-10-20 10:05:25'),
(1, 2,  5, 1,    NULL,   1, 100, '2026-10-20 10:07:00'),

-- Assessment 2: Aarav, Machine Learning, 2 of 5
(2, 2, 22, 0,    NULL,   1, 60, '2026-10-24 17:31:00'),
(2, 2, 23, 0,    NULL,   0, 85, '2026-10-24 17:32:25'),
(2, 2, 24, NULL, 'recall', 1, 120, '2026-10-24 17:34:25'),
(2, 2, 25, 1,    NULL,   0, 95, '2026-10-24 17:35:00'),
(2, 2, 26, NULL, 'I am not sure', 0, 150, '2026-10-24 17:38:30'),

-- Assessment 3: Rohan, Python, 4 of 5
(3, 4,  1, 0,    NULL,   1, 40, '2026-10-22 09:16:00'),
(3, 4,  2, 2,    NULL,   1, 50, '2026-10-22 09:17:00'),
(3, 4,  3, NULL, '[3]',  1, 75, '2026-10-22 09:18:15'),
(3, 4,  4, 1,    NULL,   0, 80, '2026-10-22 09:19:35'),
(3, 4,  5, 1,    NULL,   1, 85, '2026-10-22 09:21:00'),

-- Assessment 4: Neha, HTML/CSS, 3 of 4
(4, 7, 34, 1,    NULL,   1, 50, '2026-10-25 14:01:00'),
(4, 7, 35, 1,    NULL,   1, 60, '2026-10-25 14:02:00'),
(4, 7, 36, 1,    NULL,   0, 70, '2026-10-25 14:03:10'),
(4, 7, 37, NULL, 'media query', 1, 120, '2026-10-25 14:05:00'),

-- Assessment 5: Tanvi, Web Security, 3 of 4
(5, 9, 62, 1,    NULL,   1, 55, '2026-10-27 19:01:00'),
(5, 9, 63, 1,    NULL,   1, 70, '2026-10-27 19:02:10'),
(5, 9, 64, 1,    NULL,   1, 65, '2026-10-27 19:03:15'),
(5, 9, 65, NULL, 'plain text in the database', 0, 140, '2026-10-27 19:05:30'),

-- Assessment 6: Sneha, SQL, 4 of 5
(6, 3,  9, 1,    NULL,   1, 50, '2026-10-28 11:01:00'),
(6, 3, 10, 1,    NULL,   1, 55, '2026-10-28 11:02:00'),
(6, 3, 11, NULL, '2',    1, 90, '2026-10-28 11:03:30'),
(6, 3, 12, 1,    NULL,   0, 110, '2026-10-28 11:05:20'),
(6, 3, 13, 1,    NULL,   1, 70, '2026-10-28 11:06:30'),

-- Assessment 7: Aarav retest, Python, 4 of 5 (improvement 60 -> 80)
(7, 2,  1, 0,    NULL,   1, 35, '2026-11-02 20:00:40'),
(7, 2,  2, 2,    NULL,   1, 45, '2026-11-02 20:01:30'),
(7, 2,  3, NULL, '3',    1, 70, '2026-11-02 20:02:40'),
(7, 2,  4, 0,    NULL,   1, 85, '2026-11-02 20:04:05'),
(7, 2,  5, 0,    NULL,   0, 110, '2026-11-02 20:05:55');

-- ---------------------------------------------------------------------
-- Keep student_skills consistent with the new quiz evidence.
-- Fusion weights: self 0.30, resume 0.30, quiz 0.40 (sum = 1.00).
-- Recalculation is done by services/skill_service.py at runtime; these
-- UPDATEs just make the seeded dashboard match that formula.
-- ---------------------------------------------------------------------
UPDATE student_skills
   SET quiz_level = 4.0, current_level = ROUND(0.30*3.0 + 0.30*4.0 + 0.40*4.0, 1),
       last_source = 'hybrid'
 WHERE student_id = 2 AND skill_id = 1;     -- 3.7

UPDATE student_skills
   SET quiz_level = 2.0, current_level = ROUND(0.30*3.0 + 0.30*2.0 + 0.40*2.0, 1),
       last_source = 'hybrid'
 WHERE student_id = 2 AND skill_id = 31;    -- 2.3

UPDATE student_skills
   SET quiz_level = 4.0, current_level = ROUND(0.30*5.0 + 0.30*4.0 + 0.40*4.0, 1),
       last_source = 'hybrid'
 WHERE student_id = 4 AND skill_id = 1;     -- 4.3

UPDATE student_skills
   SET quiz_level = 4.0, current_level = ROUND(0.30*5.0 + 0.30*4.0 + 0.40*4.0, 1),
       last_source = 'hybrid'
 WHERE student_id = 7 AND skill_id = 9;     -- 4.3

UPDATE student_skills
   SET quiz_level = 4.0, current_level = ROUND(0.30*3.0 + 0.30*3.0 + 0.40*4.0, 1),
       last_source = 'hybrid'
 WHERE student_id = 9 AND skill_id = 47;    -- 3.4

UPDATE student_skills
   SET quiz_level = 4.0, current_level = ROUND(0.30*5.0 + 0.30*4.0 + 0.40*4.0, 1),
       last_source = 'hybrid'
 WHERE student_id = 3 AND skill_id = 6;     -- 4.3
