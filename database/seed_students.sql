-- =====================================================================
--  SkillTrack AI  -  database/seed_students.sql
--  1 admin + 8 demo students + their baseline skill profile.
--
--  Demo credentials (hashes below are real pbkdf2:sha256 hashes):
--      admin@skilltrack.local    /  Admin@123
--      <student email>           /  Student@123
--
--  Baseline student_skills rows carry self + resume evidence only, so
--  current_level = (self_level + resume_level) / 2, which is exactly what
--  the fusion service (A3) computes when no quiz exists. Nothing here
--  contradicts the live calculation.
-- =====================================================================

USE skilltrack_ai;

INSERT IGNORE INTO students
    (id, full_name, email, password_hash, role, phone, education, college,
     branch, year_of_study, career_goal_id, interests, weekly_hours, is_active)
VALUES
(1, 'SkillTrack Admin', 'admin@skilltrack.local',
 'pbkdf2:sha256:600000$9ddb24f9ed979785$165d0d9cf6b76fca959d2720e668718c52d9fa6813e03b292e36580b84d35942',
 'admin', NULL, NULL, NULL, NULL, NULL, NULL, NULL, 10, 1),

(2, 'Aarav Patil', 'aarav.patil@skilltrack.local',
 'pbkdf2:sha256:600000$c0e0f2d8fceeaff4$74ed0b664fd6b1af46cd1e283bfe4a42464ebcb2383251a675125d5a7f35d3d6',
 'student', '9876543210', 'B.Tech', 'AMGOI, Vathar', 'AI and ML', 2, 3,
 'Statistics, model building, Kaggle competitions', 12, 1),

(3, 'Sneha Kulkarni', 'sneha.kulkarni@skilltrack.local',
 'pbkdf2:sha256:600000$7b6bf8eb2c7a5386$dc59fcc20423cdc86c31c65ec5aeab863c731d53db39d5ee3d6ed16c7dee01b6',
 'student', '9876543211', 'B.Tech', 'AMGOI, Vathar', 'AI and ML', 2, 2,
 'Dashboards, business analytics, Excel reporting', 10, 1),

(4, 'Rohan Deshmukh', 'rohan.deshmukh@skilltrack.local',
 'pbkdf2:sha256:600000$35974cf488d07465$ec98f80b508d07c0423af814e000cf6312b09e57f153b1368fd55a5a4346f79b',
 'student', '9876543212', 'B.Tech', 'AMGOI, Vathar', 'AI and ML', 3, 1,
 'Backend APIs, automation scripts, open source', 14, 1),

(5, 'Priya Joshi', 'priya.joshi@skilltrack.local',
 'pbkdf2:sha256:600000$2498420719ce6bd3$f3b9ea16ac78a1894886f32f21a91d1b13f779dabd34877c8cd87d957da55b56',
 'student', '9876543213', 'B.Tech', 'AMGOI, Vathar', 'AI and ML', 4, 5,
 'NLP, chatbots, reading research papers', 8, 1),

(6, 'Aditya Shinde', 'aditya.shinde@skilltrack.local',
 'pbkdf2:sha256:600000$b69ddfbfbfe3ee75$6e69e095f318c999e8e31e120e6c49f0ca073bc79192a4da0158fd447940a9c6',
 'student', '9876543214', 'B.Tech', 'AMGOI, Vathar', 'AI and ML', 3, 4,
 'Model deployment, deep learning, GPU training', 16, 1),

(7, 'Neha Pawar', 'neha.pawar@skilltrack.local',
 'pbkdf2:sha256:600000$3c96e52317379782$fe00634944854c57f9bbefa6584973492e1e7fe9f9d832e8630e71650309e614',
 'student', '9876543215', 'B.Tech', 'AMGOI, Vathar', 'AI and ML', 2, 6,
 'UI design, frontend, responsive layouts', 9, 1),

(8, 'Karan Jadhav', 'karan.jadhav@skilltrack.local',
 'pbkdf2:sha256:600000$d574b40351530b0e$ed62307ce73d3c400df549277d61e6c3e029c2a87cd114ec57512befed6763be',
 'student', '9876543216', 'B.Tech', 'AMGOI, Vathar', 'AI and ML', 4, 7,
 'MERN stack, side projects, hackathons', 11, 1),

(9, 'Tanvi More', 'tanvi.more@skilltrack.local',
 'pbkdf2:sha256:600000$dc8fcc9a3e531190$046752d8322e525148f88a93d02248f0bd6cc1e5392b2e5b604ee72e071321d7',
 'student', '9876543217', 'B.Tech', 'AMGOI, Vathar', 'AI and ML', 3, 8,
 'Ethical hacking, CTF challenges, network security', 7, 1);


-- ---------------------------------------------------------------------
-- Baseline skill profiles (self + resume evidence, no quiz yet)
-- current_level = (self_level + resume_level) / 2
-- ---------------------------------------------------------------------
INSERT IGNORE INTO student_skills
    (student_id, skill_id, self_level, resume_level, quiz_level,
     current_level, evidence_count, last_source)
VALUES
-- Aarav -> Data Scientist
(2,  1, 3.0, 4.0, NULL, 3.5, 3, 'hybrid'),
(2, 27, 3.0, 3.0, NULL, 3.0, 2, 'hybrid'),
(2, 22, 4.0, 4.0, NULL, 4.0, 3, 'hybrid'),
(2, 31, 3.0, 2.0, NULL, 2.5, 2, 'hybrid'),
(2,  6, 4.0, 3.0, NULL, 3.5, 2, 'hybrid'),
(2, 28, 3.0, 3.0, NULL, 3.0, 2, 'hybrid'),

-- Sneha -> Data Analyst
(3,  6, 5.0, 4.0, NULL, 4.5, 4, 'hybrid'),
(3, 24, 5.0, 4.0, NULL, 4.5, 3, 'hybrid'),
(3,  1, 2.0, 2.0, NULL, 2.0, 1, 'hybrid'),
(3, 22, 3.0, 3.0, NULL, 3.0, 2, 'hybrid'),
(3, 27, 3.0, 2.0, NULL, 2.5, 2, 'hybrid'),
(3, 25, 3.0, 3.0, NULL, 3.0, 2, 'hybrid'),

-- Rohan -> Python Developer
(4,  1, 5.0, 4.0, NULL, 4.5, 4, 'hybrid'),
(4, 13, 3.0, 3.0, NULL, 3.0, 2, 'hybrid'),
(4,  6, 3.0, 3.0, NULL, 3.0, 2, 'hybrid'),
(4, 16, 4.0, 3.0, NULL, 3.5, 2, 'hybrid'),
(4, 15, 2.0, 2.0, NULL, 2.0, 1, 'hybrid'),
(4, 20, 2.0, 1.0, NULL, 1.5, 1, 'hybrid'),

-- Priya -> AI Engineer
(5,  1, 4.0, 4.0, NULL, 4.0, 3, 'hybrid'),
(5, 31, 4.0, 3.0, NULL, 3.5, 3, 'hybrid'),
(5, 32, 3.0, 3.0, NULL, 3.0, 2, 'hybrid'),
(5, 36, 3.0, 2.0, NULL, 2.5, 2, 'hybrid'),
(5, 35, 3.0, 2.0, NULL, 2.5, 1, 'hybrid'),
(5, 19, 3.0, 3.0, NULL, 3.0, 2, 'hybrid'),

-- Aditya -> ML Engineer
(6,  1, 5.0, 4.0, NULL, 4.5, 4, 'hybrid'),
(6, 31, 4.0, 4.0, NULL, 4.0, 4, 'hybrid'),
(6, 32, 4.0, 3.0, NULL, 3.5, 3, 'hybrid'),
(6, 34, 3.0, 3.0, NULL, 3.0, 2, 'hybrid'),
(6, 18, 2.0, 2.0, NULL, 2.0, 1, 'hybrid'),
(6, 40, 2.0, 1.0, NULL, 1.5, 1, 'hybrid'),

-- Neha -> Web Developer
(7,  9, 5.0, 4.0, NULL, 4.5, 4, 'hybrid'),
(7,  4, 4.0, 4.0, NULL, 4.0, 3, 'hybrid'),
(7, 10, 4.0, 4.0, NULL, 4.0, 2, 'hybrid'),
(7, 11, 3.0, 2.0, NULL, 2.5, 1, 'hybrid'),
(7, 16, 3.0, 3.0, NULL, 3.0, 2, 'hybrid'),
(7, 47, 2.0, 2.0, NULL, 2.0, 1, 'hybrid'),

-- Karan -> Full Stack Developer
(8,  4, 4.0, 3.0, NULL, 3.5, 3, 'hybrid'),
(8,  9, 4.0, 4.0, NULL, 4.0, 3, 'hybrid'),
(8, 11, 3.0, 3.0, NULL, 3.0, 2, 'hybrid'),
(8, 12, 3.0, 2.0, NULL, 2.5, 2, 'hybrid'),
(8, 41, 3.0, 3.0, NULL, 3.0, 2, 'hybrid'),
(8, 18, 2.0, 1.0, NULL, 1.5, 1, 'hybrid'),

-- Tanvi -> Cybersecurity Analyst
(9, 45, 4.0, 3.0, NULL, 3.5, 3, 'hybrid'),
(9, 19, 4.0, 4.0, NULL, 4.0, 3, 'hybrid'),
(9, 47, 3.0, 3.0, NULL, 3.0, 2, 'hybrid'),
(9, 46, 2.0, 2.0, NULL, 2.0, 1, 'hybrid'),
(9, 48, 2.0, 1.0, NULL, 1.5, 1, 'hybrid'),
(9,  1, 3.0, 2.0, NULL, 2.5, 1, 'hybrid');
