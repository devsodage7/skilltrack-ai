-- =====================================================================
--  SkillTrack AI  -  database/seed_careers.sql
--  8 predefined career paths. `description` + `keywords` are the document
--  used by the TF-IDF career matcher (A5), so keep them descriptive.
-- =====================================================================

USE skilltrack_ai;

INSERT IGNORE INTO careers (id, name, slug, description, keywords, is_active) VALUES
(1, 'Python Developer', 'python-developer',
 'Builds backend services, automation scripts and APIs using Python. Works with Flask or Django, relational databases, automated tests, containers and Linux servers. Writes clean reusable code and debugs production issues.',
 'python, flask, django, backend, api, rest, json, oop, scripting, automation, pytest, docker, linux, git, sql',
 1),

(2, 'Data Analyst', 'data-analyst',
 'Turns raw business data into decisions using spreadsheets, SQL and Python. Cleans messy data, writes analytical queries, builds dashboards in Power BI or Tableau and explains findings to non technical stakeholders.',
 'data analyst, sql, excel, pandas, dashboard, power bi, tableau, statistics, reporting, data cleaning, visualization, business intelligence, kpi',
 1),

(3, 'Data Scientist', 'data-scientist',
 'Builds statistical and machine learning models to answer business questions. Covers data cleaning, feature engineering, model selection, cross validation, evaluation metrics and communicating uncertainty in results.',
 'data science, statistics, machine learning, scikit-learn, pandas, feature engineering, model evaluation, python, sql, experimentation, regression, classification',
 1),

(4, 'Machine Learning Engineer', 'machine-learning-engineer',
 'Builds, trains, deploys and maintains machine learning models in production. Focus on reproducible pipelines, model serving, containers, monitoring, versioning and performance optimisation on Linux.',
 'machine learning engineer, deep learning, tensorflow, pytorch, mlops, docker, kubernetes, linux, model deployment, pipelines, monitoring, python, git',
 1),

(5, 'AI Engineer', 'ai-engineer',
 'Builds AI products using natural language processing and computer vision models, integrates them behind APIs, evaluates quality and ships them reliably to users.',
 'artificial intelligence, nlp, computer vision, deep learning, pytorch, transformers, embeddings, api, deployment, python, model serving',
 1),

(6, 'Web Developer', 'web-developer',
 'Builds responsive and accessible websites and interfaces with HTML, CSS and JavaScript. Uses modern front end tooling, consumes REST APIs and applies basic web security practices.',
 'web developer, html, css, javascript, responsive design, bootstrap, react, frontend, accessibility, git, web security, seo',
 1),

(7, 'Full Stack Developer', 'full-stack-developer',
 'Builds complete web applications end to end: responsive interfaces, server side APIs, relational database schemas, authentication, containers and deployment.',
 'full stack, javascript, react, node, express, api, rest, mysql, database, docker, git, web application, authentication',
 1),

(8, 'Cybersecurity Analyst', 'cybersecurity-analyst',
 'Monitors, detects and responds to security threats. Hardens Linux and network infrastructure, analyses logs in SIEM platforms, understands cryptography basics and follows incident response procedures.',
 'cybersecurity, networking, tcp ip, linux, web security, owasp, cryptography, siem, splunk, incident response, threat detection, penetration testing, hardening',
 1);
