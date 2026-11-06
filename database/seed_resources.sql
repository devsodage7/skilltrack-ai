-- =====================================================================
--  SkillTrack AI  -  database/seed_resources.sql
--  Free learning resources only (is_free = 1 for every row).
--  Links point to official docs, open courseware and free practice sites.
-- =====================================================================

USE skilltrack_ai;

INSERT IGNORE INTO learning_resources
    (skill_id, title, provider, url, resource_type, difficulty, est_hours, is_free)
VALUES

-- Python (1)
(1, 'The Python Tutorial (official)', 'Python Software Foundation', 'https://docs.python.org/3/tutorial/', 'docs', 'beginner', 8.0, 1),
(1, 'Python Full Course for Beginners', 'freeCodeCamp', 'https://www.youtube.com/watch?v=rfscVS0vtbw', 'video', 'beginner', 12.0, 1),
(1, 'Automate the Boring Stuff with Python', 'Al Sweigart', 'https://automatetheboringstuff.com/', 'book', 'intermediate', 20.0, 1),

-- Java (2)
(2, 'Java Tutorials', 'Oracle', 'https://docs.oracle.com/javase/tutorial/', 'docs', 'beginner', 10.0, 1),

-- C++ (3)
(3, 'C++ Language Tutorial', 'cplusplus.com', 'https://cplusplus.com/doc/tutorial/', 'docs', 'beginner', 10.0, 1),

-- JavaScript (4)
(4, 'JavaScript Guide', 'MDN Web Docs', 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide', 'docs', 'beginner', 10.0, 1),
(4, 'JavaScript30 - 30 small projects', 'Wes Bos', 'https://javascript30.com/', 'practice', 'intermediate', 15.0, 1),

-- TypeScript (5)
(5, 'TypeScript Handbook', 'Microsoft', 'https://www.typescriptlang.org/docs/handbook/intro.html', 'docs', 'intermediate', 8.0, 1),

-- SQL (6)
(6, 'SQLBolt - interactive SQL lessons', 'SQLBolt', 'https://sqlbolt.com/', 'practice', 'beginner', 6.0, 1),
(6, 'SQL Tutorial', 'Mode Analytics', 'https://mode.com/sql-tutorial/', 'course', 'intermediate', 8.0, 1),

-- R (7)
(7, 'R for Data Science (2e)', 'Hadley Wickham', 'https://r4ds.hadley.nz/', 'book', 'intermediate', 20.0, 1),

-- Bash (8)
(8, 'Bash Scripting Tutorial', 'Ryan Chadwick', 'https://ryanstutorials.net/bash-scripting-tutorial/', 'course', 'beginner', 6.0, 1),

-- HTML/CSS (9)
(9, 'Learn Web Development', 'MDN Web Docs', 'https://developer.mozilla.org/en-US/docs/Learn', 'course', 'beginner', 12.0, 1),
(9, 'CSS Flexbox Complete Guide', 'CSS-Tricks', 'https://css-tricks.com/snippets/css/a-guide-to-flexbox/', 'docs', 'intermediate', 3.0, 1),

-- Bootstrap (10)
(10, 'Bootstrap 5 Documentation', 'Bootstrap Team', 'https://getbootstrap.com/docs/5.3/getting-started/introduction/', 'docs', 'beginner', 5.0, 1),

-- React (11)
(11, 'React - Learn the basics', 'Meta', 'https://react.dev/learn', 'docs', 'beginner', 10.0, 1),
(11, 'React Tutorial for Beginners', 'freeCodeCamp', 'https://www.youtube.com/watch?v=bMknfKXIFA8', 'video', 'beginner', 11.0, 1),

-- Node.js (12)
(12, 'Node.js Learn', 'OpenJS Foundation', 'https://nodejs.org/en/learn', 'docs', 'beginner', 8.0, 1),

-- Flask (13)
(13, 'Flask Tutorial (official)', 'Pallets', 'https://flask.palletsprojects.com/en/stable/tutorial/', 'docs', 'beginner', 8.0, 1),

-- Django (14)
(14, 'Django Tutorial (official)', 'Django Software Foundation', 'https://docs.djangoproject.com/en/stable/intro/tutorial01/', 'docs', 'beginner', 10.0, 1),

-- REST API (15)
(15, 'REST API Design Tutorial', 'restfulapi.net', 'https://restfulapi.net/', 'docs', 'intermediate', 4.0, 1),

-- Git (16)
(16, 'Pro Git Book (free)', 'Scott Chacon', 'https://git-scm.com/book/en/v2', 'book', 'beginner', 8.0, 1),

-- GitHub (17)
(17, 'GitHub Quickstart', 'GitHub', 'https://docs.github.com/en/get-started/quickstart', 'docs', 'beginner', 3.0, 1),

-- Docker (18)
(18, 'Docker Get Started', 'Docker Inc', 'https://docs.docker.com/get-started/', 'docs', 'beginner', 6.0, 1),

-- Linux (19)
(19, 'Linux Journey', 'Linux Journey', 'https://linuxjourney.com/', 'course', 'beginner', 10.0, 1),

-- Unit Testing (20)
(20, 'pytest Documentation', 'pytest Team', 'https://docs.pytest.org/en/stable/', 'docs', 'intermediate', 5.0, 1),

-- CI/CD (21)
(21, 'GitHub Actions Quickstart', 'GitHub', 'https://docs.github.com/en/actions/quickstart', 'docs', 'intermediate', 4.0, 1),

-- Pandas (22)
(22, '10 minutes to pandas', 'pandas Team', 'https://pandas.pydata.org/docs/user_guide/10min.html', 'docs', 'beginner', 3.0, 1),
(22, 'Pandas Course', 'Kaggle Learn', 'https://www.kaggle.com/learn/pandas', 'course', 'intermediate', 6.0, 1),

-- NumPy (23)
(23, 'NumPy Absolute Beginners Guide', 'NumPy Team', 'https://numpy.org/doc/stable/user/absolute_beginners.html', 'docs', 'beginner', 4.0, 1),

-- Excel (24)
(24, 'Excel Formulas and Functions', 'ExcelJet', 'https://exceljet.net/', 'practice', 'beginner', 6.0, 1),

-- Power BI (25)
(25, 'Power BI Learning Path', 'Microsoft Learn', 'https://learn.microsoft.com/en-us/power-bi/', 'course', 'beginner', 10.0, 1),

-- Tableau (26)
(26, 'Tableau Free Training Videos', 'Tableau', 'https://www.tableau.com/learn/training/20201', 'video', 'beginner', 8.0, 1),

-- Statistics (27)
(27, 'Statistics and Probability', 'Khan Academy', 'https://www.khanacademy.org/math/statistics-probability', 'course', 'beginner', 15.0, 1),
(27, 'StatQuest with Josh Starmer', 'StatQuest', 'https://www.youtube.com/@statquest', 'video', 'intermediate', 12.0, 1),

-- Data Cleaning (28)
(28, 'Data Cleaning', 'Kaggle Learn', 'https://www.kaggle.com/learn/data-cleaning', 'course', 'beginner', 4.0, 1),

-- Data Visualization (29)
(29, 'From Data to Viz', 'Yan Holtz', 'https://www.data-to-viz.com/', 'docs', 'intermediate', 4.0, 1),

-- ETL (30)
(30, 'What is ETL?', 'IBM', 'https://www.ibm.com/think/topics/etl', 'docs', 'beginner', 2.0, 1),

-- Machine Learning (31)
(31, 'Machine Learning Crash Course', 'Google Developers', 'https://developers.google.com/machine-learning/crash-course', 'course', 'beginner', 15.0, 1),
(31, 'Machine Learning Specialization (audit)', 'DeepLearning.AI', 'https://www.coursera.org/specializations/machine-learning-introduction', 'course', 'intermediate', 30.0, 1),

-- Deep Learning (32)
(32, 'Dive into Deep Learning', 'D2L.ai', 'https://d2l.ai/', 'book', 'advanced', 40.0, 1),

-- Scikit-learn (33)
(33, 'Scikit-learn User Guide', 'scikit-learn Team', 'https://scikit-learn.org/stable/user_guide.html', 'docs', 'intermediate', 10.0, 1),

-- TensorFlow (34)
(34, 'TensorFlow Tutorials', 'Google', 'https://www.tensorflow.org/tutorials', 'docs', 'intermediate', 12.0, 1),

-- PyTorch (35)
(35, 'PyTorch Tutorials', 'Meta', 'https://pytorch.org/tutorials/', 'docs', 'intermediate', 12.0, 1),

-- NLP (36)
(36, 'Hugging Face NLP Course', 'Hugging Face', 'https://huggingface.co/learn/nlp-course', 'course', 'intermediate', 20.0, 1),
(36, 'Natural Language Processing with Python', 'NLTK', 'https://www.nltk.org/book/', 'book', 'advanced', 25.0, 1),

-- Computer Vision (37)
(37, 'OpenCV Tutorials', 'OpenCV', 'https://docs.opencv.org/4.x/d9/df8/tutorial_root.html', 'docs', 'intermediate', 12.0, 1),

-- Model Evaluation (38)
(38, 'Metrics and scoring', 'scikit-learn Team', 'https://scikit-learn.org/stable/modules/model_evaluation.html', 'docs', 'intermediate', 5.0, 1),

-- Feature Engineering (39)
(39, 'Feature Engineering', 'Kaggle Learn', 'https://www.kaggle.com/learn/feature-engineering', 'course', 'intermediate', 5.0, 1),

-- MLOps (40)
(40, 'Made With ML - MLOps Course', 'Goku Mohandas', 'https://madewithml.com/', 'course', 'advanced', 25.0, 1),

-- MySQL (41)
(41, 'MySQL 8.0 Reference Manual - Tutorial', 'Oracle', 'https://dev.mysql.com/doc/refman/8.0/en/tutorial.html', 'docs', 'beginner', 8.0, 1),

-- PostgreSQL (42)
(42, 'PostgreSQL Tutorial', 'postgresqltutorial.com', 'https://www.postgresqltutorial.com/', 'course', 'beginner', 8.0, 1),

-- MongoDB (43)
(43, 'MongoDB Manual - Getting Started', 'MongoDB Inc', 'https://www.mongodb.com/docs/manual/tutorial/getting-started/', 'docs', 'beginner', 6.0, 1),

-- Database Design (44)
(44, 'Database Normalization Basics', 'Microsoft Learn', 'https://learn.microsoft.com/en-us/office/troubleshoot/access/database-normalization', 'docs', 'intermediate', 4.0, 1),

-- Networking (45)
(45, 'How the Internet Works', 'Cloudflare Learning', 'https://www.cloudflare.com/learning/network-layer/what-is-a-computer-network/', 'docs', 'beginner', 6.0, 1),
(45, 'Computer Networking Full Course', 'freeCodeCamp', 'https://www.youtube.com/watch?v=qiQR5rTSshw', 'video', 'beginner', 9.0, 1),

-- Cryptography (46)
(46, 'CryptoHack - free cryptography challenges', 'CryptoHack', 'https://cryptohack.org/', 'practice', 'advanced', 20.0, 1),

-- Web Security (47)
(47, 'OWASP Top 10', 'OWASP Foundation', 'https://owasp.org/www-project-top-ten/', 'docs', 'intermediate', 6.0, 1),
(47, 'PortSwigger Web Security Academy', 'PortSwigger', 'https://portswigger.net/web-security', 'practice', 'intermediate', 25.0, 1),

-- SIEM (48)
(48, 'Splunk Free Training', 'Splunk', 'https://www.splunk.com/en_us/training/free-courses/overview.html', 'course', 'beginner', 8.0, 1),

-- Penetration Testing (49)
(49, 'TryHackMe - free rooms', 'TryHackMe', 'https://tryhackme.com/', 'practice', 'beginner', 20.0, 1),

-- Incident Response (50)
(50, 'NIST Incident Response Guide (SP 800-61r2)', 'NIST', 'https://csrc.nist.gov/pubs/sp/800/61/r2/final', 'docs', 'advanced', 6.0, 1),

-- Soft skills also used by the roadmap
(4, 'Clean Code in JavaScript', 'MDN Web Docs', 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide', 'docs', 'intermediate', 4.0, 1);
