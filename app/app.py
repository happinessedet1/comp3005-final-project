#!/usr/bin/env python3
"""
Simple CLI (command line interface) app for the Gym Management DB project.

Roles:
- Member
- Trainer
- Admin

"""

import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime

# DB CONFIG

DB_NAME = "happinessedet"
DB_USER = "happinessedet"
DB_PASSWORD = ""
DB_HOST = "localhost"
DB_PORT = 5432


def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )


# Helper utilities

def prompt_int(msg):
    while True:
        val = input(msg).strip()
        if val == "":
            return None
        try:
            return int(val)
        except ValueError:
            print("Please enter a valid integer or leave blank.")


def prompt_float(msg):
    while True:
        val = input(msg).strip()
        if val == "":
            return None
        try:
            return float(val)
        except ValueError:
            print("Please enter a valid number or leave blank.")


def print_rows(rows):
    if not rows:
        print("No results.")
        return
    for row in rows:
        print("-----")
        for k, v in row.items():
            print(f"{k}: {v}")


# MEMBER OPERATIONS

def member_register(conn):
    print("\n=== Member Registration ===")
    full_name = input("Full name: ").strip()
    email = input("Email: ").strip()
    dob_str = input("Date of birth (YYYY-MM-DD, optional): ").strip()
    gender = input("Gender (optional): ").strip()
    phone = input("Phone (optional): ").strip()
    address = input("Address (optional): ").strip()

    dob = None
    if dob_str:
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format. Leaving date_of_birth NULL.")

    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO member (full_name, email, date_of_birth, gender, phone, address)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING member_id;
                """,
                (full_name, email, dob, gender or None, phone or None, address or None),
            )
            member_id = cur.fetchone()[0]
            conn.commit()
            print(f"Member created with ID: {member_id}")
        except psycopg2.Error as e:
            conn.rollback()
            print("Error creating member:", e)


def member_log_health_metric(conn, member_id):
    print("\n=== Log Health Metric ===")
    weight = prompt_float("Weight (kg): ")
    body_fat = prompt_float("Body fat (%): ")
    hr = prompt_int("Resting heart rate (bpm): ")
    notes = input("Notes (optional): ").strip() or None

    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO health_metric (member_id, weight_kg, body_fat_percent, resting_hr, notes)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (member_id, weight, body_fat, hr, notes),
            )
            conn.commit()
            print("Health metric logged.")
        except psycopg2.Error as e:
            conn.rollback()
            print("Error logging health metric:", e)


def member_view_dashboard(conn, member_id):
    print("\n=== Member Dashboard ===")
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            "SELECT * FROM member_dashboard WHERE member_id = %s;",
            (member_id,),
        )
        row = cur.fetchone()
        if not row:
            print("No dashboard data (member not found or no metrics yet).")
        else:
            print_rows([row])


def member_register_class(conn, member_id):
    print("\n=== Register for Class ===")
    class_id = prompt_int("Class session ID: ")
    if class_id is None:
        print("Class session ID is required.")
        return

    with conn.cursor() as cur:
        try:
            # Check capacity vs registrations
            cur.execute(
                """
                SELECT
                    COALESCE(cs.capacity, r.capacity) AS max_cap,
                    COUNT(rg.member_id) AS current_count
                FROM class_session cs
                JOIN room r ON r.room_id = cs.room_id
                LEFT JOIN member_class_registration rg
                  ON rg.class_session_id = cs.class_session_id
                WHERE cs.class_session_id = %s
                GROUP BY cs.class_session_id, max_cap;
                """,
                (class_id,),
            )
            row = cur.fetchone()
            if not row:
                print("Class session not found.")
                return

            max_cap, current_count = row
            if current_count >= max_cap:
                print("Class is full. Cannot register.")
                return

            # Register
            cur.execute(
                """
                INSERT INTO member_class_registration (member_id, class_session_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (member_id, class_id),
            )
            conn.commit()
            print("You are registered for the class.")
        except psycopg2.Error as e:
            conn.rollback()
            print("Error registering for class:", e)


def member_book_pt(conn, member_id):
    print("\n=== Book PT Session ===")
    trainer_id = prompt_int("Trainer ID: ")
    room_id = prompt_int("Room ID: ")
    start_str = input("Start time (YYYY-MM-DD HH:MM): ").strip()
    end_str = input("End time (YYYY-MM-DD HH:MM): ").strip()

    if not (trainer_id and room_id and start_str and end_str):
        print("All fields are required.")
        return

    try:
        start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
    except ValueError:
        print("Invalid datetime format.")
        return

    with conn.cursor() as cur:
        try:
            # Check trainer availability
            cur.execute(
                """
                SELECT 1
                FROM trainer_availability a
                WHERE a.trainer_id = %s
                  AND a.start_time <= %s
                  AND a.end_time   >= %s
                LIMIT 1;
                """,
                (trainer_id, start_time, end_time),
            )
            if cur.fetchone() is None:
                print("Trainer not available in that time window.")
                return

            # Check overlapping PT sessions for trainer
            cur.execute(
                """
                SELECT 1
                FROM pt_session p
                WHERE p.trainer_id = %s
                  AND p.status = 'SCHEDULED'
                  AND NOT (%s <= p.start_time OR %s >= p.end_time)
                LIMIT 1;
                """,
                (trainer_id, start_time, end_time),
            )
            if cur.fetchone() is not None:
                print("Trainer already has a PT session in that time.")
                return

            # Check overlapping classes for trainer
            cur.execute(
                """
                SELECT 1
                FROM class_session cs
                WHERE cs.trainer_id = %s
                  AND cs.status = 'SCHEDULED'
                  AND NOT (%s <= cs.start_time OR %s >= cs.end_time)
                LIMIT 1;
                """,
                (trainer_id, start_time, end_time),
            )
            if cur.fetchone() is not None:
                print("Trainer has a class in that time.")
                return

            # If all good, insert the PT session
            cur.execute(
                """
                INSERT INTO pt_session (member_id, trainer_id, room_id, start_time, end_time)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING pt_session_id;
                """,
                (member_id, trainer_id, room_id, start_time, end_time),
            )
            pt_id = cur.fetchone()[0]
            conn.commit()
            print(f"PT session booked with ID: {pt_id}")
        except psycopg2.Error as e:
            conn.rollback()
            print("Error booking PT session:", e)


def member_menu(conn):
    print("\n=== MEMBER MENU ===")
    print("1. Register new member")
    print("2. Use existing member")
    choice = input("Choose: ").strip()

    if choice == "1":
        member_register(conn)
        return

    member_id = prompt_int("Enter your member ID: ")
    if not member_id:
        print("Member ID required.")
        return

    while True:
        print("\nMember actions:")
        print("1. View dashboard")
        print("2. Log health metric")
        print("3. Register for class")
        print("4. Book PT session")
        print("0. Back to main menu")
        c = input("Choose: ").strip()
        if c == "1":
            member_view_dashboard(conn, member_id)
        elif c == "2":
            member_log_health_metric(conn, member_id)
        elif c == "3":
            member_register_class(conn, member_id)
        elif c == "4":
            member_book_pt(conn, member_id)
        elif c == "0":
            break
        else:
            print("Invalid choice.")
            

# TRAINER OPERATIONS

def trainer_set_availability(conn, trainer_id):
    print("\n=== Set Availability ===")
    start_str = input("Start (YYYY-MM-DD HH:MM): ").strip()
    end_str = input("End   (YYYY-MM-DD HH:MM): ").strip()
    try:
        start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
    except ValueError:
        print("Invalid datetime.")
        return

    with conn.cursor() as cur:
        try:
            # overlap check
            cur.execute(
                """
                SELECT 1
                FROM trainer_availability a
                WHERE a.trainer_id = %s
                  AND NOT (%s <= a.start_time OR %s >= a.end_time)
                LIMIT 1;
                """,
                (trainer_id, start_time, end_time),
            )
            if cur.fetchone() is not None:
                print("Overlaps with existing availability.")
                return

            cur.execute(
                """
                INSERT INTO trainer_availability (trainer_id, start_time, end_time)
                VALUES (%s, %s, %s);
                """,
                (trainer_id, start_time, end_time),
            )
            conn.commit()
            print("Availability added.")
        except psycopg2.Error as e:
            conn.rollback()
            print("Error setting availability:", e)


def trainer_view_schedule(conn, trainer_id):
    print("\n=== Trainer Schedule (upcoming) ===")
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            SELECT 'PT' AS kind, pt_session_id AS id, start_time, end_time, room_id
            FROM pt_session
            WHERE trainer_id = %s AND start_time >= NOW() AND status = 'SCHEDULED'
            UNION ALL
            SELECT 'CLASS' AS kind, class_session_id AS id, start_time, end_time, room_id
            FROM class_session
            WHERE trainer_id = %s AND start_time >= NOW() AND status = 'SCHEDULED'
            ORDER BY start_time;
            """,
            (trainer_id, trainer_id),
        )
        rows = cur.fetchall()
        print_rows(rows)


def trainer_menu(conn):
    trainer_id = prompt_int("\nEnter trainer ID: ")
    if not trainer_id:
        print("Trainer ID required.")
        return

    while True:
        print("\nTRAINER MENU")
        print("1. Set availability")
        print("2. View schedule")
        print("0. Back to main menu")
        c = input("Choose: ").strip()
        if c == "1":
            trainer_set_availability(conn, trainer_id)
        elif c == "2":
            trainer_view_schedule(conn, trainer_id)
        elif c == "0":
            break
        else:
            print("Invalid choice.")


# ADMIN OPERATIONS

def admin_create_class_session(conn):
    print("\n=== Create Class Session ===")
    class_type_id = prompt_int("Class type ID: ")
    trainer_id = prompt_int("Trainer ID: ")
    room_id = prompt_int("Room ID: ")
    start_str = input("Start (YYYY-MM-DD HH:MM): ").strip()
    end_str = input("End   (YYYY-MM-DD HH:MM): ").strip()
    capacity = prompt_int("Capacity (optional, ENTER for NULL): ")

    if not (class_type_id and trainer_id and room_id and start_str and end_str):
        print("Missing required fields.")
        return

    try:
        start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
    except ValueError:
        print("Invalid datetime.")
        return

    with conn.cursor() as cur:
        try:
            # Overlap check for room
            cur.execute(
                """
                SELECT 1
                FROM class_session cs
                WHERE cs.room_id = %s
                  AND cs.status = 'SCHEDULED'
                  AND NOT (%s <= cs.start_time OR %s >= cs.end_time)
                LIMIT 1;
                """,
                (room_id, start_time, end_time),
            )
            if cur.fetchone() is not None:
                print("Room already booked for that time.")
                return

            # Overlap check for trainer
            cur.execute(
                """
                SELECT 1
                FROM class_session cs
                WHERE cs.trainer_id = %s
                  AND cs.status = 'SCHEDULED'
                  AND NOT (%s <= cs.start_time OR %s >= cs.end_time)
                LIMIT 1;
                """,
                (trainer_id, start_time, end_time),
            )
            if cur.fetchone() is not None:
                print("Trainer already has a class at that time.")
                return

            # Insert
            cur.execute(
                """
                INSERT INTO class_session
                  (class_type_id, trainer_id, room_id, start_time, end_time, capacity)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING class_session_id;
                """,
                (class_type_id, trainer_id, room_id, start_time, end_time, capacity),
            )
            cs_id = cur.fetchone()[0]
            conn.commit()
            print(f"Class session created with ID: {cs_id}")
        except psycopg2.Error as e:
            conn.rollback()
            print("Error creating class session:", e)


def admin_record_payment(conn):
    print("\n=== Record Payment ===")
    invoice_id = prompt_int("Invoice ID: ")
    amount = prompt_float("Amount: ")
    method = input("Method (cash/card/...): ").strip()

    if not (invoice_id and amount and method):
        print("All fields are required.")
        return

    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO payment (invoice_id, amount, method)
                VALUES (%s, %s, %s)
                RETURNING payment_id;
                """,
                (invoice_id, amount, method),
            )
            payment_id = cur.fetchone()[0]
            conn.commit()
            print(f"Payment recorded with ID: {payment_id}")
            print("Invoice status should be updated automatically by trigger.")
        except psycopg2.Error as e:
            conn.rollback()
            print("Error recording payment:", e)


def admin_menu(conn):
    while True:
        print("\nADMIN MENU")
        print("1. Create class session")
        print("2. Record payment")
        print("0. Back to main menu")
        c = input("Choose: ").strip()
        if c == "1":
            admin_create_class_session(conn)
        elif c == "2":
            admin_record_payment(conn)
        elif c == "0":
            break
        else:
            print("Invalid choice.")


# MAIN LOOP

def main():
    print("Gym Management CLI")

    conn = get_connection()
    try:
        while True:
            print("\n=== MAIN MENU ===")
            print("1. Member")
            print("2. Trainer")
            print("3. Admin")
            print("0. Quit")
            choice = input("Choose role: ").strip()
            if choice == "1":
                member_menu(conn)
            elif choice == "2":
                trainer_menu(conn)
            elif choice == "3":
                admin_menu(conn)
            elif choice == "0":
                break
            else:
                print("Invalid choice.")
    finally:
        conn.close()
        print("Goodbye.")


if __name__ == "__main__":
    main()
