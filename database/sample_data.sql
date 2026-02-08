-- Sample Data for Testing

-- Insert Sample User
INSERT INTO users (email, password_hash, full_name, phone) VALUES
('test@example.com', 'hashed_password_here', 'John Doe', '+91-9876543210');

-- Insert Sample Companies
INSERT INTO companies (name, website, industry, location) VALUES
('Google', 'https://www.google.com', 'Technology', 'Bangalore, India'),
('Microsoft', 'https://www.microsoft.com', 'Technology', 'Hyderabad, India'),
('Amazon', 'https://www.amazon.com', 'E-commerce', 'Bangalore, India'),
('TCS', 'https://www.tcs.com', 'IT Services', 'Mumbai, India'),
('Infosys', 'https://www.infosys.com', 'IT Services', 'Bangalore, India');

-- Insert Sample Skills
INSERT INTO skills (name, category) VALUES
('Python', 'Programming'),
('Java', 'Programming'),
('SQL', 'Programming'),
('React', 'Framework'),
('FastAPI', 'Framework'),
('Spring Boot', 'Framework'),
('Docker', 'Tool'),
('Git', 'Tool'),
('Communication', 'Soft Skill'),
('Problem Solving', 'Soft Skill');

-- Insert Sample Applications
INSERT INTO applications (user_id, company_id, job_title, job_description, status, applied_date, job_type, location) VALUES
(1, 1, 'Software Engineer', 'Develop scalable web applications', 'applied', '2025-10-01', 'Full-time', 'Bangalore'),
(1, 2, 'Backend Developer', 'Build backend APIs', 'screening', '2025-09-28', 'Full-time', 'Hyderabad'),
(1, 3, 'Full Stack Developer', 'Work on end-to-end features', 'interview_scheduled', '2025-09-25', 'Full-time', 'Bangalore');

-- Insert Sample Interview Questions
INSERT INTO interview_questions (company_id, job_role, question, question_type, difficulty, topic) VALUES
(1, 'Software Engineer', 'Explain the difference between SQL and NoSQL databases', 'Technical', 'Medium', 'Databases'),
(1, 'Software Engineer', 'Tell me about a time you faced a challenging bug', 'Behavioral', 'Easy', 'Problem Solving'),
(2, 'Backend Developer', 'How do you handle authentication in REST APIs?', 'Technical', 'Medium', 'Security'),
(3, 'Full Stack Developer', 'Design a URL shortener service', 'Technical', 'Hard', 'System Design');
