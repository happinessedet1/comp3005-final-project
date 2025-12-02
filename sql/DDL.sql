-- Core entities

CREATE TABLE member (
    member_id      SERIAL PRIMARY KEY,
    full_name      VARCHAR(100) NOT NULL,
    email          VARCHAR(100) NOT NULL UNIQUE,
    date_of_birth  DATE,
    gender         VARCHAR(20),
    phone          VARCHAR(30),
    address        TEXT,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE trainer (
    trainer_id     SERIAL PRIMARY KEY,
    full_name      VARCHAR(100) NOT NULL,
    email          VARCHAR(100) NOT NULL UNIQUE,
    phone          VARCHAR(30),
    specialization VARCHAR(100)
);

CREATE TABLE staff (
    staff_id   SERIAL PRIMARY KEY,
    full_name  VARCHAR(100) NOT NULL,
    email      VARCHAR(100) NOT NULL UNIQUE,
    role       VARCHAR(30) NOT NULL DEFAULT 'ADMIN',
    phone      VARCHAR(30)
);

CREATE TABLE room (
    room_id   SERIAL PRIMARY KEY,
    name      VARCHAR(50) NOT NULL UNIQUE,
    location  VARCHAR(100),
    capacity  INT NOT NULL CHECK (capacity > 0)
);

CREATE TABLE class_type (
    class_type_id            SERIAL PRIMARY KEY,
    name                     VARCHAR(50) NOT NULL UNIQUE,
    description              TEXT,
    default_duration_minutes INT CHECK (default_duration_minutes > 0)
);


-- Scheduling / bookings

CREATE TABLE class_session (
    class_session_id  SERIAL PRIMARY KEY,
    class_type_id     INT NOT NULL REFERENCES class_type(class_type_id),
    trainer_id        INT NOT NULL REFERENCES trainer(trainer_id),
    room_id           INT NOT NULL REFERENCES room(room_id),
    start_time        TIMESTAMP NOT NULL,
    end_time          TIMESTAMP NOT NULL,
    capacity          INT CHECK (capacity IS NULL OR capacity > 0),
    status            VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED',
    CHECK (end_time > start_time)
);

CREATE TABLE pt_session (
    pt_session_id  SERIAL PRIMARY KEY,
    member_id      INT NOT NULL REFERENCES member(member_id),
    trainer_id     INT NOT NULL REFERENCES trainer(trainer_id),
    room_id        INT NOT NULL REFERENCES room(room_id),
    start_time     TIMESTAMP NOT NULL,
    end_time       TIMESTAMP NOT NULL,
    status         VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED',
    notes          TEXT,
    CHECK (end_time > start_time)
);

CREATE TABLE trainer_availability (
    availability_id  SERIAL PRIMARY KEY,
    trainer_id       INT NOT NULL REFERENCES trainer(trainer_id),
    start_time       TIMESTAMP NOT NULL,
    end_time         TIMESTAMP NOT NULL,
    CHECK (end_time > start_time)
);

CREATE TABLE member_class_registration (
    member_id        INT NOT NULL REFERENCES member(member_id),
    class_session_id INT NOT NULL REFERENCES class_session(class_session_id),
    registered_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    attendance_status VARCHAR(20) NOT NULL DEFAULT 'REGISTERED',
    PRIMARY KEY (member_id, class_session_id)
);


-- Goals & health data

CREATE TABLE fitness_goal (
    goal_id       SERIAL PRIMARY KEY,
    member_id     INT NOT NULL REFERENCES member(member_id),
    goal_type     VARCHAR(50) NOT NULL,
    target_value  NUMERIC(8,2),
    unit          VARCHAR(20),
    start_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    target_date   DATE,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE health_metric (
    metric_id         SERIAL PRIMARY KEY,
    member_id         INT NOT NULL REFERENCES member(member_id),
    recorded_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    weight_kg         NUMERIC(5,2),
    body_fat_percent  NUMERIC(5,2),
    resting_hr        INT,
    notes             TEXT
);


-- Equipment & maintenance

CREATE TABLE equipment (
    equipment_id  SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    room_id       INT REFERENCES room(room_id),
    status        VARCHAR(20) NOT NULL DEFAULT 'OK'
);

CREATE TABLE maintenance_log (
    maintenance_id       SERIAL PRIMARY KEY,
    equipment_id         INT NOT NULL REFERENCES equipment(equipment_id),
    reported_by_staff_id INT NOT NULL REFERENCES staff(staff_id),
    issue_description    TEXT NOT NULL,
    reported_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    status               VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    resolved_at          TIMESTAMP
);


-- Billing

CREATE TABLE invoice (
    invoice_id    SERIAL PRIMARY KEY,
    member_id     INT NOT NULL REFERENCES member(member_id),
    created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    due_date      DATE,
    total_amount  NUMERIC(10,2) NOT NULL CHECK (total_amount >= 0),
    status        VARCHAR(20) NOT NULL DEFAULT 'PENDING'
);

CREATE TABLE invoice_line (
    line_id      SERIAL PRIMARY KEY,
    invoice_id   INT NOT NULL REFERENCES invoice(invoice_id) ON DELETE CASCADE,
    item_type    VARCHAR(30) NOT NULL,
    item_id      INT,
    description  TEXT NOT NULL,
    quantity     INT NOT NULL CHECK (quantity > 0),
    unit_price   NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE payment (
    payment_id  SERIAL PRIMARY KEY,
    invoice_id  INT NOT NULL REFERENCES invoice(invoice_id) ON DELETE CASCADE,
    paid_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    amount      NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    method      VARCHAR(20) NOT NULL
);


-- VIEW: Member Dashboard

CREATE OR REPLACE VIEW member_dashboard AS
SELECT
    m.member_id,
    m.full_name,
    m.email,
    lm.recorded_at AS last_metric_time,
    lm.weight_kg,
    lm.body_fat_percent,
    lm.resting_hr,
    COALESCE(c_stats.past_classes, 0)         AS past_classes,
    COALESCE(pt_stats.upcoming_pt_sessions, 0) AS upcoming_pt_sessions
FROM member m
LEFT JOIN LATERAL (
    SELECT h.*
    FROM health_metric h
    WHERE h.member_id = m.member_id
    ORDER BY h.recorded_at DESC
    LIMIT 1
) lm ON TRUE
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS past_classes
    FROM member_class_registration r
    JOIN class_session cs
      ON cs.class_session_id = r.class_session_id
    WHERE r.member_id = m.member_id
      AND cs.start_time < NOW()
      AND r.attendance_status = 'ATTENDED'
) c_stats ON TRUE
LEFT JOIN LATERAL (
    SELECT COUNT(*) AS upcoming_pt_sessions
    FROM pt_session p
    WHERE p.member_id = m.member_id
      AND p.start_time >= NOW()
      AND p.status = 'SCHEDULED'
) pt_stats ON TRUE;


-- INDEXES

-- Speed up trainer schedule queries
CREATE INDEX idx_pt_session_trainer_time
    ON pt_session(trainer_id, start_time);

CREATE INDEX idx_class_session_trainer_time
    ON class_session(trainer_id, start_time);

-- speed up lookups by class_session in registration table
CREATE INDEX idx_member_class_registration_session
    ON member_class_registration(class_session_id);


-- TRIGGER: update invoice status after payments

CREATE OR REPLACE FUNCTION update_invoice_status()
RETURNS TRIGGER AS $$
DECLARE
    paid_sum NUMERIC(10,2);
    total    NUMERIC(10,2);
BEGIN
    SELECT COALESCE(SUM(amount), 0) INTO paid_sum
    FROM payment
    WHERE invoice_id = NEW.invoice_id;

    SELECT total_amount INTO total
    FROM invoice
    WHERE invoice_id = NEW.invoice_id;

    IF paid_sum = 0 THEN
        UPDATE invoice SET status = 'PENDING'
        WHERE invoice_id = NEW.invoice_id;
    ELSIF paid_sum < total THEN
        UPDATE invoice SET status = 'PARTIALLY_PAID'
        WHERE invoice_id = NEW.invoice_id;
    ELSE
        UPDATE invoice SET status = 'PAID'
        WHERE invoice_id = NEW.invoice_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_invoice_status
AFTER INSERT OR UPDATE ON payment
FOR EACH ROW
EXECUTE FUNCTION update_invoice_status();
