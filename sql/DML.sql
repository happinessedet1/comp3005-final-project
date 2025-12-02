-- Members
INSERT INTO member (full_name, email, date_of_birth, gender, phone, address)
VALUES
 ('Alex Johnson', 'alex@example.com', '1995-03-10', 'F', '555-1111', '123 Main St'),
 ('John Smith',   'john@example.com', '1990-07-21', 'M', '555-2222', '456 Oak Ave'),
 ('Sam Lee',      'sam@example.com',  '1998-12-05', 'F', '555-3333', '789 Pine Rd');

-- Trainers
INSERT INTO trainer (full_name, email, phone, specialization)
VALUES
 ('Taylor Coach', 'taylor@club.com', '555-4444', 'Strength'),
 ('Jordan Flex',  'jordan@club.com', '555-5555', 'Cardio & HIIT');

-- Staff
INSERT INTO staff (full_name, email, role, phone)
VALUES
 ('Admin One', 'admin1@club.com', 'ADMIN', '555-0001'),
 ('Admin Two', 'admin2@club.com', 'ADMIN', '555-0002');

-- Rooms
INSERT INTO room (name, location, capacity)
VALUES
 ('Studio A', '1st Floor', 20),
 ('Studio B', '1st Floor', 15),
 ('PT Room 1', '2nd Floor', 2);

-- Class types
INSERT INTO class_type (name, description, default_duration_minutes)
VALUES
 ('Yoga', 'Relaxing flexibility session', 60),
 ('Spin', 'High-intensity cycling', 45);
('bolw', 'cardio',50);


-- Trainer availability
INSERT INTO trainer_availability (trainer_id, start_time, end_time)
VALUES
 (1, '2025-11-30 09:00', '2025-11-30 12:00'),
 (1, '2025-12-01 09:00', '2025-12-01 12:00'),
 (2, '2025-11-30 17:00', '2025-11-30 20:00');

-- Class sessions
INSERT INTO class_session (class_type_id, trainer_id, room_id, start_time, end_time, capacity)
VALUES
 (1, 1, 1, '2025-11-30 10:00', '2025-11-30 11:00', 20),
 (2, 2, 2, '2025-11-30 18:00', '2025-11-30 18:45', 15);

-- Member registrations
INSERT INTO member_class_registration (member_id, class_session_id, attendance_status)
VALUES
 (1, 1, 'REGISTERED'),
 (2, 1, 'ATTENDED'),
 (1, 2, 'REGISTERED');

-- PT sessions
INSERT INTO pt_session (member_id, trainer_id, room_id, start_time, end_time, status)
VALUES
 (1, 1, 3, '2025-12-01 10:00', '2025-12-01 11:00', 'SCHEDULED'),
 (2, 1, 3, '2025-12-01 11:00', '2025-12-01 12:00', 'SCHEDULED');

-- Goals
INSERT INTO fitness_goal (member_id, goal_type, target_value, unit, start_date, target_date)
VALUES
 (1, 'WEIGHT', 65.0, 'kg', CURRENT_DATE, CURRENT_DATE + INTERVAL '90 days'),
 (1, 'BODY_FAT', 22.0, '%', CURRENT_DATE, CURRENT_DATE + INTERVAL '120 days');

-- Health metrics
INSERT INTO health_metric (member_id, weight_kg, body_fat_percent, resting_hr)
VALUES
 (1, 80.0, 28.0, 75),
 (1, 78.0, 27.0, 72),
 (2, 90.0, 30.0, 80);

-- Equipment
INSERT INTO equipment (name, room_id, status)
VALUES
 ('Treadmill 1', 2, 'OK'),
 ('Bike 1',      2, 'OK');

-- Maintenance
INSERT INTO maintenance_log (equipment_id, reported_by_staff_id, issue_description)
VALUES
 (1, 1, 'Strange noise from belt');

-- Billing & payments
INSERT INTO invoice (member_id, due_date, total_amount)
VALUES
 (1, CURRENT_DATE + INTERVAL '7 days', 150.00);

INSERT INTO invoice_line (invoice_id, item_type, item_id, description, quantity, unit_price)
VALUES
 (1, 'PT_SESSION', 1, 'Personal training session', 1, 80.00),
 (1, 'CLASS', 1, 'Yoga class pack', 1, 70.00);

INSERT INTO payment (invoice_id, amount, method)
VALUES
 (1, 80.00, 'CARD');
-- trigger will set status to PARTIALLY_PAID
