-- ============================================================
-- AI-Powered Registration Intelligence & Attendee Management
-- Database Schema (SQLite)
-- ============================================================

DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS admins;
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS venues;
DROP TABLE IF EXISTS speakers;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS conflict_log;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    college TEXT NOT NULL,
    department TEXT NOT NULL,
    gender TEXT NOT NULL,
    city TEXT NOT NULL,
    participant_category TEXT NOT NULL,
    attendance_mode TEXT NOT NULL,
    registration_id TEXT UNIQUE,
    checked_in INTEGER DEFAULT 0,
    qr_code TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin', -- admin / organizer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'Present',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    date TEXT,
    capacity INTEGER DEFAULT 100,
    description TEXT
);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type TEXT NOT NULL,
    generated_by TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path TEXT
);

CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    subject TEXT,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed events
INSERT INTO events (name, category, date, capacity, description) VALUES
('AI & ML Summit', 'Technical', '2026-09-12', 200, 'A deep dive into modern AI and Machine Learning practices.'),
('Startup Pitch Fest', 'Business', '2026-09-14', 150, 'Pitch your startup idea to industry experts.'),
('Cultural Fiesta', 'Cultural', '2026-09-18', 300, 'A vibrant celebration of art, music and dance.'),
('Hackathon 2026', 'Technical', '2026-09-20', 250, '24-hour coding marathon for innovators.'),
('Sports Meet', 'Sports', '2026-09-22', 400, 'Inter-college sports championship.');

-- ============================================================
-- MILESTONE 2 — VENUE & SPEAKER OPERATIONS
-- ============================================================

CREATE TABLE venues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT,
    capacity INTEGER NOT NULL DEFAULT 0,
    room_type TEXT,
    facilities TEXT,                 -- comma-separated list
    status TEXT NOT NULL DEFAULT 'Available',  -- Available / Maintenance
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE speakers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    organization TEXT,
    designation TEXT,
    expertise TEXT,                  -- comma-separated topics
    bio TEXT,
    preferred_session_type TEXT,
    available_dates TEXT,            -- comma-separated YYYY-MM-DD
    available_slots TEXT,            -- e.g. "09:00-18:00"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    session_type TEXT,
    session_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    expected_attendees INTEGER DEFAULT 0,
    required_facilities TEXT,        -- comma-separated list
    venue_id INTEGER,
    speaker_id INTEGER,
    status TEXT NOT NULL DEFAULT 'Scheduled',  -- Upcoming/Scheduled/Completed/Cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (venue_id) REFERENCES venues(id) ON DELETE SET NULL,
    FOREIGN KEY (speaker_id) REFERENCES speakers(id) ON DELETE SET NULL
);

CREATE TABLE conflict_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conflict_type TEXT NOT NULL,     -- venue / speaker
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed venues
INSERT INTO venues (name, location, capacity, room_type, facilities, status) VALUES
('Main Auditorium', 'Block A, Ground Floor', 300, 'Auditorium', 'Projector,Microphone,Speakers,Stage,Air Conditioning,Recording Equipment,Wi-Fi', 'Available'),
('Seminar Hall 1', 'Block B, 1st Floor', 120, 'Seminar Hall', 'Projector,Microphone,Speakers,Wi-Fi,Air Conditioning', 'Available'),
('Computer Lab 3', 'Block C, 2nd Floor', 60, 'Computer Lab', 'Projector,Wi-Fi,Air Conditioning,Video Conferencing', 'Available'),
('Conference Room A', 'Block A, 3rd Floor', 40, 'Conference Room', 'Smart Board,Microphone,Wi-Fi,Video Conferencing,Air Conditioning', 'Available'),
('Workshop Hall', 'Block D, Ground Floor', 150, 'Workshop Hall', 'Projector,Smart Board,Microphone,Speakers,Wi-Fi', 'Available'),
('Open Air Arena', 'Central Lawn', 500, 'Outdoor Arena', 'Stage,Speakers,Microphone', 'Maintenance');

-- Seed speakers
INSERT INTO speakers (name, email, phone, organization, designation, expertise, bio, preferred_session_type, available_dates, available_slots) VALUES
('Dr. Ananya Rao', 'ananya.rao@example.com', '9876543210', 'Infosys', 'Principal AI Architect', 'Artificial Intelligence, Machine Learning, Deep Learning', 'Dr. Rao leads applied AI research and has delivered keynotes at major technical summits.', 'Keynote', '2026-09-12,2026-09-20', '09:00-18:00'),
('Rahul Mehta', 'rahul.mehta@example.com', '9876543211', 'TechNova Solutions', 'Senior Software Engineer', 'Cloud Computing, DevOps, Kubernetes', 'Rahul specializes in scalable cloud-native systems and enjoys mentoring hackathon teams.', 'Workshop', '2026-09-20,2026-09-14', '10:00-17:00'),
('Priya Sundaram', 'priya.sundaram@example.com', '9876543212', 'DataWorks Analytics', 'Data Science Lead', 'Data Science, Analytics, Python, Machine Learning', 'Priya has 10+ years of experience building data-driven products and loves hands-on workshops.', 'Technical Session', '2026-09-12,2026-09-18', '09:00-16:00'),
('Karan Verma', 'karan.verma@example.com', '9876543213', 'StartUp Hub', 'Founder & CEO', 'Entrepreneurship, Business Strategy, Startups', 'Karan has founded two startups and regularly mentors early-stage founders on pitching.', 'Panel Discussion', '2026-09-14', '11:00-18:00'),
('Sneha Iyer', 'sneha.iyer@example.com', '9876543214', 'CyberSafe Labs', 'Cybersecurity Consultant', 'Cybersecurity, Ethical Hacking, Network Security', 'Sneha trains organizations on security best practices and has spoken at multiple tech conferences.', 'Training', '2026-09-20,2026-09-22', '09:00-15:00');

-- Seed sessions
INSERT INTO sessions (title, description, session_type, session_date, start_time, end_time, expected_attendees, required_facilities, venue_id, speaker_id, status) VALUES
('Opening Keynote: The Future of AI', 'A keynote on where artificial intelligence is headed over the next decade.', 'Keynote', '2026-09-12', '09:30', '10:30', 280, 'Projector,Microphone,Speakers,Stage', 1, 1, 'Scheduled'),
('Hands-on Kubernetes Workshop', 'A practical workshop on deploying containerized applications with Kubernetes.', 'Workshop', '2026-09-20', '10:00', '12:30', 55, 'Projector,Wi-Fi', 3, 2, 'Scheduled'),
('Data Science in Practice', 'A technical session covering real-world data science pipelines.', 'Technical Session', '2026-09-12', '11:00', '12:30', 110, 'Projector,Microphone,Wi-Fi', 2, 3, 'Scheduled'),
('Founders Panel: Building a Startup', 'A panel discussion with founders sharing lessons from building companies.', 'Panel Discussion', '2026-09-14', '14:00', '15:30', 130, 'Smart Board,Microphone,Wi-Fi', 5, 4, 'Upcoming');

-- ============================================================
-- MILESTONE 3 — SPONSORSHIP & INCIDENT MANAGEMENT
-- ============================================================

DROP TABLE IF EXISTS sponsors;
DROP TABLE IF EXISTS sponsor_contacts;
DROP TABLE IF EXISTS sponsor_interactions;
DROP TABLE IF EXISTS sponsor_followups;
DROP TABLE IF EXISTS sponsorship_opportunities;
DROP TABLE IF EXISTS incidents;
DROP TABLE IF EXISTS incident_updates;
DROP TABLE IF EXISTS operational_alerts;

CREATE TABLE sponsors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    industry TEXT,
    website TEXT,
    location TEXT,
    target_audience TEXT,
    keywords TEXT,                      -- comma-separated
    sponsorship_category TEXT,          -- Title/Platinum/Gold/Silver/Bronze/In-Kind/Media Partner
    budget_potential TEXT,              -- Low / Medium / High / Very High
    estimated_budget INTEGER DEFAULT 0, -- INR, rough estimate used in scoring/analytics
    contact_person TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    suitability_score INTEGER DEFAULT 0,
    match_category TEXT,                -- Excellent Match / Good Match / Moderate Match / Low Match
    score_explanation TEXT,
    status TEXT NOT NULL DEFAULT 'Discovered',
    source TEXT DEFAULT 'Manual Entry', -- Directory / Manual Entry / Referral
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sponsor_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sponsor_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    designation TEXT,
    email TEXT,
    phone TEXT,
    is_primary INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sponsor_id) REFERENCES sponsors(id) ON DELETE CASCADE
);

CREATE TABLE sponsor_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sponsor_id INTEGER NOT NULL,
    interaction_type TEXT NOT NULL,     -- Discovery/Evaluation/Outreach/Response/Follow-Up/Negotiation/Confirmation/Rejection/Note
    communication_method TEXT,          -- Email/Phone/LinkedIn/Meeting/Website Contact Form/Other/System
    subject TEXT,
    message TEXT,
    sponsor_response TEXT,
    next_action TEXT,
    follow_up_date TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sponsor_id) REFERENCES sponsors(id) ON DELETE CASCADE
);

CREATE TABLE sponsor_followups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sponsor_id INTEGER NOT NULL,
    due_date TEXT NOT NULL,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'Pending',   -- Pending / Completed / Rescheduled
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sponsor_id) REFERENCES sponsors(id) ON DELETE CASCADE
);

CREATE TABLE sponsorship_opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sponsor_id INTEGER NOT NULL,
    package TEXT,
    benefits TEXT,
    amount_requested REAL DEFAULT 0,
    amount_committed REAL DEFAULT 0,
    amount_received REAL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Proposed',  -- Proposed / Negotiating / Confirmed / Rejected
    confirmed_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sponsor_id) REFERENCES sponsors(id) ON DELETE CASCADE
);

CREATE TABLE incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,             -- Technical/Venue/Speaker/Session/Registration/Attendance/Sponsorship/Security/Operational/Participant/Other
    priority TEXT NOT NULL DEFAULT 'Medium',   -- Low/Medium/High/Critical
    status TEXT NOT NULL DEFAULT 'Reported',   -- Reported/Assigned/In Progress/Resolved/Verified/Closed
    related_venue_id INTEGER,
    related_session_id INTEGER,
    related_speaker_id INTEGER,
    related_sponsor_id INTEGER,
    reported_by TEXT,
    assigned_to TEXT,
    due_date TEXT,
    recommendation TEXT,
    resolution TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (related_venue_id) REFERENCES venues(id) ON DELETE SET NULL,
    FOREIGN KEY (related_session_id) REFERENCES sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (related_speaker_id) REFERENCES speakers(id) ON DELETE SET NULL,
    FOREIGN KEY (related_sponsor_id) REFERENCES sponsors(id) ON DELETE SET NULL
);

CREATE TABLE incident_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id INTEGER NOT NULL,
    update_text TEXT NOT NULL,
    status_change TEXT,
    updated_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE
);

CREATE TABLE operational_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL DEFAULT 'Info',    -- Info/Warning/High/Critical
    module TEXT NOT NULL,                     -- Sponsorship/Incident/Venue/Speaker/Session
    related_entity_type TEXT,
    related_entity_id INTEGER,
    is_read INTEGER DEFAULT 0,
    is_resolved INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed sponsors demonstrating the full discovery -> confirmation workflow
INSERT INTO sponsors (company_name, industry, website, location, target_audience, keywords, sponsorship_category,
    budget_potential, estimated_budget, contact_person, contact_email, contact_phone, suitability_score,
    match_category, score_explanation, status, source, notes, created_at) VALUES
('NexaCloud Technologies', 'Technology', 'https://nexacloud.example.com', 'Bengaluru', 'Students, Developers, AI Professionals',
 'AI, cloud, machine learning, developers', 'Gold Sponsor', 'High', 300000, 'Meera Krishnan', 'meera.k@nexacloud.example.com',
 '9845012345', 92, 'Excellent Match',
 'Recommended because the company''s technology industry directly matches the AI/ML Summit, its target audience of developers and AI professionals aligns closely with expected attendees, and it has strong high-budget sponsorship potential.',
 'Confirmed', 'Directory', 'Confirmed as Gold Sponsor after two rounds of negotiation.', datetime('now','-21 days')),
('BrightPath EduTech', 'Education', 'https://brightpathedu.example.com', 'Bengaluru', 'Students, College Faculty',
 'edtech, learning, student outreach, colleges', 'Silver Sponsor', 'Medium', 120000, 'Arvind Nair', 'arvind@brightpathedu.example.com',
 '9845012346', 78, 'Good Match',
 'Recommended because the education industry aligns with the student-heavy audience, and the company has previously shown interest in college-run technical events, though budget potential is moderate.',
 'Negotiating', 'Directory', 'Awaiting final sign-off from their marketing head.', datetime('now','-18 days')),
('FinEdge Capital', 'Finance', 'https://finedgecapital.example.com', 'Mumbai', 'Professionals, Startups',
 'fintech, investment, startups, finance', 'Bronze Sponsor', 'Medium', 90000, 'Rohit Sharma', 'rohit.sharma@finedge.example.com',
 '9845012347', 61, 'Moderate Match',
 'Recommended with caution because finance has moderate relevance to a technology-focused summit; audience overlap exists mainly through the startup and professional segments.',
 'Follow-up Required', 'Manual Entry', 'Responded with interest but needs a formal proposal.', datetime('now','-14 days')),
('CareWell Health Systems', 'Healthcare', 'https://carewellhealth.example.com', 'Bengaluru', 'General Public, Professionals',
 'healthcare, wellness, medical technology', 'In-Kind Sponsor', 'Low', 40000, 'Dr. Sunita Rao', 'sunita.rao@carewellhealth.example.com',
 '9845012348', 38, 'Low Match',
 'Lower relevance because the healthcare industry has limited overlap with an AI/technology event audience, though the company could still contribute an in-kind wellness booth.',
 'Discovered', 'Directory', NULL, datetime('now','-10 days')),
('Zenith Foods & Beverages', 'Food & Beverage', 'https://zenithfnb.example.com', 'Bengaluru', 'Students, General Attendees',
 'catering, refreshments, F&B, campus events', 'In-Kind Sponsor', 'Low', 50000, 'Kavya Menon', 'kavya.menon@zenithfnb.example.com',
 '9845012349', 55, 'Moderate Match',
 'Moderate relevance as a catering/refreshments sponsor for a large student audience; strong logistical fit though limited strategic/brand alignment with the AI theme.',
 'Contacted', 'Manual Entry', 'Outreach email sent; follow-up scheduled.', datetime('now','-8 days')),
('UrbanDrive Motors', 'Automotive', 'https://urbandrivemotors.example.com', 'Chennai', 'Professionals, General Public',
 'automotive, electric vehicles, mobility', 'Bronze Sponsor', 'Medium', 100000, 'Vikram Iyer', 'vikram.iyer@urbandrive.example.com',
 '9845012350', 45, 'Low Match',
 'Limited direct relevance to an AI/ML-focused summit, though the company''s EV/mobility technology angle gives some strategic overlap worth exploring.',
 'Rejected', 'Directory', 'Declined citing no marketing budget allocated for campus events this quarter.', datetime('now','-25 days')),
('MediaWave Broadcasting', 'Media', 'https://mediawavebc.example.com', 'Bengaluru', 'General Public, Media',
 'media coverage, broadcasting, press, publicity', 'Media Partner', 'Medium', 80000, 'Divya Pillai', 'divya.pillai@mediawave.example.com',
 '9845012351', 70, 'Good Match',
 'Good fit as a media partner — strong ability to amplify event coverage and reach a wider audience, aligning well with visibility goals even though direct budget contribution is modest.',
 'Interested', 'Directory', 'Interested in a media-partner barter arrangement.', datetime('now','-6 days')),
('ConnectTel Communications', 'Telecommunications', 'https://connecttel.example.com', 'Hyderabad', 'Students, Professionals, Developers',
 'telecom, 5G, connectivity, networking', 'Silver Sponsor', 'High', 200000, 'Anil Kapoor', 'anil.kapoor@connecttel.example.com',
 '9845012352', 84, 'Excellent Match',
 'Recommended because telecommunications infrastructure is highly relevant to a technology summit, the target audience of developers and professionals matches well, and budget potential is high.',
 'Proposal Sent', 'Directory', 'Formal proposal sent; awaiting response by follow-up date.', datetime('now','-5 days')),
('LaunchPad Ventures', 'Startups', 'https://launchpadventures.example.com', 'Bengaluru', 'Students, Founders, Investors',
 'startups, venture capital, incubation, entrepreneurship', 'Gold Sponsor', 'High', 250000, 'Neha Gupta', 'neha.gupta@launchpad.example.com',
 '9845012353', 88, 'Excellent Match',
 'Recommended because the startup ecosystem focus matches the event''s entrepreneurship and technology themes closely, with strong audience compatibility among student founders and high budget potential.',
 'Shortlisted', 'Directory', 'Shortlisted after evaluation; outreach message drafted, not yet sent.', datetime('now','-4 days')),
('Metro Retail Group', 'Retail', 'https://metroretailgroup.example.com', 'Bengaluru', 'General Public, Students',
 'retail, consumer brands, campus marketing', 'Bronze Sponsor', 'Low', 40000, 'Sanjay Bhatt', 'sanjay.bhatt@metroretail.example.com',
 '9845012354', 42, 'Low Match', 'Limited strategic relevance to an AI/technology summit; primarily useful for general brand visibility.',
 'Potential', 'Manual Entry', NULL, datetime('now','-2 days'));

-- Sponsor interaction / communication history (activity timeline)
INSERT INTO sponsor_interactions (sponsor_id, interaction_type, communication_method, subject, message, sponsor_response, next_action, follow_up_date, created_by, created_at) VALUES
(1, 'Discovery', 'System', 'Sponsor discovered via directory search', 'Added to sponsor directory after matching "technology, AI" keyword search.', NULL, 'Run suitability evaluation', NULL, 'System Admin', datetime('now','-21 days')),
(1, 'Evaluation', 'System', 'Suitability score generated', 'Sponsorship Agent scored this sponsor 92% — Excellent Match.', NULL, 'Shortlist sponsor', NULL, 'System Admin', datetime('now','-20 days')),
(1, 'Outreach', 'Email', 'Sponsorship Proposal — AI & ML Summit 2026', 'Sent outreach email introducing the AI & ML Summit and requesting Gold Sponsor participation.', NULL, 'Await response', datetime('now','-16 days'), 'Event Organizer', datetime('now','-19 days')),
(1, 'Response', 'Email', 'Re: Sponsorship Proposal', 'Sponsor replied expressing strong interest and requested a call.', 'Interested — requested a call to discuss package details.', 'Schedule call', datetime('now','-15 days'), 'Event Organizer', datetime('now','-17 days')),
(1, 'Negotiation', 'Meeting', 'Sponsorship package discussion', 'Discussed Gold Sponsor package, benefits and branding placement on a video call.', 'Agreed in principle to Gold Sponsor package.', 'Send confirmation paperwork', NULL, 'Event Organizer', datetime('now','-14 days')),
(1, 'Confirmation', 'Email', 'Sponsorship Confirmed', 'Sponsor confirmed participation as Gold Sponsor with committed amount of ₹3,00,000.', 'Confirmed — payment to follow after agreement is signed.', 'Track payment receipt', NULL, 'Event Organizer', datetime('now','-21 days')),

(2, 'Discovery', 'System', 'Sponsor discovered via directory search', 'Added to sponsor directory under Education category.', NULL, 'Run suitability evaluation', NULL, 'System Admin', datetime('now','-18 days')),
(2, 'Outreach', 'Email', 'Sponsorship Proposal — AI & ML Summit 2026', 'Sent outreach email proposing a Silver Sponsor package.', NULL, 'Await response', datetime('now','-11 days'), 'Event Organizer', datetime('now','-16 days')),
(2, 'Response', 'Phone', 'Follow-up call', 'Called to follow up on the emailed proposal.', 'Interested, needs internal budget approval.', 'Follow up after approval', datetime('now','+2 days'), 'Event Organizer', datetime('now','-9 days')),
(2, 'Negotiation', 'Email', 'Package finalization', 'Shared finalized Silver Sponsor benefits document for sign-off.', 'Reviewing internally, awaiting marketing head approval.', 'Await sign-off', datetime('now','+2 days'), 'Event Organizer', datetime('now','-3 days')),

(3, 'Discovery', 'System', 'Sponsor discovered via manual entry', 'Organizer manually recorded this sponsor after a networking event.', NULL, 'Run suitability evaluation', NULL, 'Event Organizer', datetime('now','-14 days')),
(3, 'Outreach', 'LinkedIn', 'Sponsorship Introduction', 'Sent a LinkedIn message introducing the event and sponsorship opportunity.', NULL, 'Await response', datetime('now','-6 days'), 'Event Organizer', datetime('now','-12 days')),
(3, 'Response', 'LinkedIn', 'Re: Sponsorship Introduction', 'Contact responded showing interest but requested a formal proposal document.', 'Interested — requested a formal written proposal.', 'Send formal proposal and follow up', datetime('now','+1 days'), 'Event Organizer', datetime('now','-7 days')),

(5, 'Discovery', 'System', 'Sponsor discovered via directory search', 'Added to sponsor directory under Food & Beverage category.', NULL, 'Run suitability evaluation', NULL, 'System Admin', datetime('now','-8 days')),
(5, 'Outreach', 'Email', 'Catering Sponsorship Proposal', 'Proposed an in-kind catering sponsorship for the event.', NULL, 'Await response', datetime('now','+3 days'), 'Event Organizer', datetime('now','-5 days')),

(6, 'Discovery', 'System', 'Sponsor discovered via directory search', 'Added to sponsor directory under Automotive category.', NULL, 'Run suitability evaluation', NULL, 'System Admin', datetime('now','-25 days')),
(6, 'Outreach', 'Email', 'Sponsorship Proposal', 'Sent outreach proposal requesting Bronze Sponsor participation.', NULL, 'Await response', datetime('now','-20 days'), 'Event Organizer', datetime('now','-23 days')),
(6, 'Rejection', 'Email', 'Re: Sponsorship Proposal', 'Sponsor declined the sponsorship request.', 'Rejected — no marketing budget allocated for campus events this quarter.', 'Mark inactive, revisit next cycle', NULL, 'Event Organizer', datetime('now','-25 days')),

(7, 'Discovery', 'System', 'Sponsor discovered via directory search', 'Added to sponsor directory under Media category.', NULL, 'Run suitability evaluation', NULL, 'System Admin', datetime('now','-6 days')),
(7, 'Outreach', 'Email', 'Media Partnership Proposal', 'Proposed a media-partner barter arrangement for event coverage.', NULL, 'Await response', datetime('now','+4 days'), 'Event Organizer', datetime('now','-4 days')),
(7, 'Response', 'Email', 'Re: Media Partnership Proposal', 'Contact responded positively to the barter arrangement idea.', 'Interested in a media-partner barter arrangement.', 'Finalize coverage terms', datetime('now','+4 days'), 'Event Organizer', datetime('now','-2 days')),

(8, 'Discovery', 'System', 'Sponsor discovered via directory search', 'Added to sponsor directory under Telecommunications category.', NULL, 'Run suitability evaluation', NULL, 'System Admin', datetime('now','-5 days')),
(8, 'Evaluation', 'System', 'Suitability score generated', 'Sponsorship Agent scored this sponsor 84% — Excellent Match.', NULL, 'Shortlist and approach', NULL, 'System Admin', datetime('now','-5 days')),
(8, 'Outreach', 'Email', 'Sponsorship Proposal — Silver Package', 'Sent a formal sponsorship proposal for the Silver Sponsor package.', NULL, 'Await response by follow-up date', datetime('now','+1 days'), 'Event Organizer', datetime('now','-3 days')),

(9, 'Discovery', 'System', 'Sponsor discovered via directory search', 'Added to sponsor directory under Startups category.', NULL, 'Run suitability evaluation', NULL, 'System Admin', datetime('now','-4 days')),
(9, 'Evaluation', 'System', 'Suitability score generated', 'Sponsorship Agent scored this sponsor 88% — Excellent Match.', NULL, 'Shortlist sponsor', NULL, 'System Admin', datetime('now','-4 days'));

-- Follow-ups (due today / overdue / upcoming)
INSERT INTO sponsor_followups (sponsor_id, due_date, reason, status, created_at) VALUES
(3, date('now'), 'Follow up after internal budget approval for Bronze Sponsor package.', 'Pending', datetime('now','-9 days')),
(2, date('now','+2 days'), 'Check whether marketing head has signed off on Silver Sponsor package.', 'Pending', datetime('now','-3 days')),
(7, date('now','+4 days'), 'Finalize media coverage terms for the barter arrangement.', 'Pending', datetime('now','-2 days')),
(8, date('now','+1 days'), 'Check for response to the Silver Sponsor proposal.', 'Pending', datetime('now','-3 days')),
(5, date('now','-2 days'), 'Follow up on catering sponsorship proposal — no response yet.', 'Pending', datetime('now','-5 days'));

-- Sponsorship opportunities (confirmed / in-progress deals)
INSERT INTO sponsorship_opportunities (sponsor_id, package, benefits, amount_requested, amount_committed, amount_received, status, confirmed_date, created_at) VALUES
(1, 'Gold Sponsor', 'Logo on main stage backdrop, 5-minute address slot, branded booth, social media mentions, logo on all attendee badges', 300000, 300000, 150000, 'Confirmed', date('now','-2 days'), datetime('now','-14 days')),
(2, 'Silver Sponsor', 'Logo on website and banners, booth space, mention during opening keynote', 120000, 0, 0, 'Negotiating', NULL, datetime('now','-9 days')),
(8, 'Silver Sponsor', 'Logo on website and banners, booth space, session sponsorship for Kubernetes Workshop', 200000, 0, 0, 'Proposed', NULL, datetime('now','-3 days')),
(6, 'Bronze Sponsor', 'Logo on website footer, single social media mention', 100000, 0, 0, 'Rejected', NULL, datetime('now','-23 days'));

-- Seed incidents demonstrating the full report -> resolution workflow
INSERT INTO incidents (title, description, category, priority, status, related_venue_id, related_session_id, related_speaker_id, related_sponsor_id, reported_by, assigned_to, due_date, recommendation, resolution, created_at, resolved_at) VALUES
('Projector malfunction in Main Auditorium', 'The main projector started flickering and shut off twice during setup, 30 minutes before the opening keynote.',
 'Venue', 'Critical', 'Closed', 1, 1, NULL, NULL, 'Event Organizer', 'Facilities Team',
 date('now','-11 days'),
 'Immediately notify the event organizer and venue manager. Reassign the affected session to an available suitable venue if possible, or arrange a backup projector before the session start time.',
 'Backup projector was installed from Computer Lab 3 within 20 minutes; keynote started on time with no attendee-facing disruption.',
 datetime('now','-12 days'), datetime('now','-12 days')),

('Keynote speaker delayed in transit', 'Dr. Ananya Rao informed the team she is stuck in traffic and may arrive 15-20 minutes after the scheduled keynote start time.',
 'Speaker', 'High', 'Resolved', 1, 1, 1, NULL, 'Event Organizer', 'Event Organizer',
 date('now','-11 days'),
 'Check the Speaker Agent for alternative speakers with matching expertise and availability, or adjust the schedule by moving a later session earlier to absorb the delay.',
 'Opening remarks and sponsor acknowledgements were moved ahead of the keynote to absorb the 15-minute delay; session proceeded without cancellation.',
 datetime('now','-12 days'), datetime('now','-11 days')),

('Double-booking risk flagged for Seminar Hall 1', 'The Smart Scheduler flagged a potential overlap between two technical sessions requested for the same time slot.',
 'Session', 'Medium', 'Verified', 2, 3, NULL, NULL, 'Event Organizer', 'Event Organizer',
 date('now','-8 days'),
 'Use the existing Smart Scheduler and conflict detection system to identify alternative time slots or an alternate venue with matching facilities.',
 'One session was moved to Computer Lab 3 after confirming facility compatibility; no scheduling conflict occurred.',
 datetime('now','-9 days'), datetime('now','-8 days')),

('Registration desk queue causing delays', 'Long queues formed at the registration desk during peak morning check-in, causing attendees to miss the first 10 minutes of sessions.',
 'Registration', 'Medium', 'In Progress', NULL, NULL, NULL, NULL, 'Volunteer Coordinator', 'Volunteer Coordinator',
 date('now','+1 days'),
 'Open an additional QR check-in counter and direct volunteers to help attendees pre-load their Registration ID to speed up scanning.',
 NULL, datetime('now','-2 days'), NULL),

('Sponsor follow-up overdue for catering proposal', 'Zenith Foods & Beverages has not responded to the catering sponsorship proposal sent 5 days ago; the scheduled follow-up date has passed.',
 'Sponsorship', 'Low', 'Assigned', NULL, NULL, NULL, 5, 'Event Organizer', 'Event Organizer',
 date('now','+2 days'),
 'Review sponsor communication history and assign a follow-up action to the sponsorship team; consider a phone call if email follow-up gets no response.',
 NULL, datetime('now','-1 days'), NULL),

('Wi-Fi congestion in Workshop Hall', 'Multiple attendees reported slow or dropped Wi-Fi connections during the hands-on workshop session, affecting the ability to follow along.',
 'Technical', 'High', 'Reported', 5, NULL, NULL, NULL, 'Volunteer Coordinator', NULL,
 date('now','+1 days'),
 'Immediately notify the venue manager and IT support to check access point load; consider temporarily capping non-essential device connections in the hall.',
 NULL, datetime('now'), NULL);

INSERT INTO incident_updates (incident_id, update_text, status_change, updated_by, created_at) VALUES
(1, 'Incident reported by the organizer during pre-keynote setup checks.', 'Reported', 'Event Organizer', datetime('now','-12 days')),
(1, 'Critical priority assigned; Facilities Team notified immediately.', 'Assigned', 'Event Organizer', datetime('now','-12 days')),
(1, 'Facilities team investigating projector and checking for a backup unit.', 'In Progress', 'Facilities Team', datetime('now','-12 days')),
(1, 'Backup projector installed from Computer Lab 3; keynote proceeded on schedule.', 'Resolved', 'Facilities Team', datetime('now','-12 days')),
(1, 'Verified with organizer that the keynote ran without further issues.', 'Closed', 'Event Organizer', datetime('now','-11 days')),

(2, 'Incident reported after speaker informed the team of a transit delay.', 'Reported', 'Event Organizer', datetime('now','-12 days')),
(2, 'High priority assigned given imminent keynote start time.', 'Assigned', 'Event Organizer', datetime('now','-12 days')),
(2, 'Agenda reshuffled to absorb the delay; monitoring speaker arrival.', 'In Progress', 'Event Organizer', datetime('now','-12 days')),
(2, 'Speaker arrived and keynote proceeded; incident resolved.', 'Resolved', 'Event Organizer', datetime('now','-11 days')),

(3, 'Incident logged automatically after Smart Scheduler flagged an overlap.', 'Reported', 'Event Organizer', datetime('now','-9 days')),
(3, 'Medium priority assigned; reviewing venue alternatives.', 'Assigned', 'Event Organizer', datetime('now','-9 days')),
(3, 'Session reassigned to Computer Lab 3 after facility check.', 'Resolved', 'Event Organizer', datetime('now','-8 days')),
(3, 'Verified no conflict remains in the scheduler.', 'Verified', 'Event Organizer', datetime('now','-8 days')),

(4, 'Incident reported by volunteer coordinator after observing long queues.', 'Reported', 'Volunteer Coordinator', datetime('now','-2 days')),
(4, 'Assigned to volunteer coordinator to open an additional check-in counter.', 'Assigned', 'Event Organizer', datetime('now','-2 days')),
(4, 'Second QR check-in counter opened; queue length being monitored.', 'In Progress', 'Volunteer Coordinator', datetime('now','-1 days')),

(5, 'Incident logged after follow-up date passed with no sponsor response.', 'Reported', 'Event Organizer', datetime('now','-1 days')),
(5, 'Assigned to sponsorship follow-up owner for a phone call attempt.', 'Assigned', 'Event Organizer', datetime('now','-1 days')),

(6, 'Incident reported by volunteer coordinator during the workshop session.', 'Reported', 'Volunteer Coordinator', datetime('now'));

-- Seed operational alerts
INSERT INTO operational_alerts (title, description, severity, module, related_entity_type, related_entity_id, is_read, is_resolved, created_at) VALUES
('Critical incident reported: Projector malfunction', 'A critical-priority incident was reported in Main Auditorium requiring immediate attention.', 'Critical', 'Incident', 'incident', 1, 1, 1, datetime('now','-12 days')),
('High-priority incident reported: Speaker delayed', 'Keynote speaker Dr. Ananya Rao reported a transit delay before the opening keynote.', 'High', 'Incident', 'incident', 2, 1, 1, datetime('now','-12 days')),
('High-priority incident open: Wi-Fi congestion', 'Wi-Fi congestion reported in Workshop Hall is still open and unassigned.', 'High', 'Incident', 'incident', 6, 0, 0, datetime('now')),
('Incident not yet assigned', 'The Wi-Fi congestion incident has not been assigned to a responsible person.', 'Warning', 'Incident', 'incident', 6, 0, 0, datetime('now')),
('Sponsor follow-up overdue', 'Follow-up for Zenith Foods & Beverages was due 2 days ago and has not been completed.', 'Warning', 'Sponsorship', 'sponsor', 5, 0, 0, datetime('now','-2 days')),
('Follow-up due today', 'A scheduled follow-up with FinEdge Capital is due today.', 'Info', 'Sponsorship', 'sponsor', 3, 0, 0, datetime('now')),
('Sponsor awaiting response', 'ConnectTel Communications has not responded to the Silver Sponsor proposal sent recently.', 'Info', 'Sponsorship', 'sponsor', 8, 0, 0, datetime('now','-3 days')),
('Confirmed sponsor requires action', 'NexaCloud Technologies has only received partial payment against the committed sponsorship amount.', 'Warning', 'Sponsorship', 'sponsor', 1, 0, 0, datetime('now','-2 days'));

-- Seed default admin (password: admin123, hashed in app on first run)
