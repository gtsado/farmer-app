import sqlite3
import pandas as pd
import uuid
import os
import json
from datetime import datetime
import math


# Path to your SQLite database file
DB_PATH = os.path.join(os.path.dirname(__file__), "ecowise-mvp.db")

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # cursor.execute("PRAGMA foreign_keys = OFF;")
    # cursor.execute("DROP TABLE IF EXISTS invoice;")
    # cursor.execute("DROP TABLE IF EXISTS tips;")
    # cursor.execute("DROP TABLE IF EXISTS tokens;")
    # cursor.execute("DROP TABLE IF EXISTS bundle_lenders;")
    # cursor.execute("DROP TABLE IF EXISTS bundle_sacks;")
    # cursor.execute("DROP TABLE IF EXISTS bundles;")
    # cursor.execute("DROP TABLE IF EXISTS lenders;")
    # cursor.execute("DROP TABLE IF EXISTS batch_bags;")
    # cursor.execute("DROP TABLE IF EXISTS batches;")
    # cursor.execute("DROP TABLE IF EXISTS warrant_receipts;")
    # cursor.execute("DROP TABLE IF EXISTS bag_sacks;")
    # cursor.execute("DROP TABLE IF EXISTS bags;")
    # cursor.execute("DROP TABLE IF EXISTS sacks;")
    # cursor.execute("DROP TABLE IF EXISTS farmers;")
    # cursor.execute("PRAGMA foreign_keys = ON;")


    # FARMERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS farmers (
        id TEXT PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT,
        country TEXT,
        city TEXT,
        gender TEXT,
        phone_number TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # SACKS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sacks (
        id TEXT PRIMARY KEY,
        farmer_id INTEGER NOT NULL,
        weight_kg REAL NOT NULL,
        value_paid REAL NOT NULL,
        delivered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        warehouse TEXT,
        debt_token_minted BOOLEAN DEFAULT 0,
        FOREIGN KEY (farmer_id) REFERENCES farmers(id)
    );
    """)

    # BAGS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bags (
        id TEXT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # BAG_SACKS (Many-to-Many)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bag_sacks (
        bag_id TEXT,
        sack_id TEXT,
        allocated_weight_kg REAL NOT NULL,
        PRIMARY KEY (bag_id, sack_id),
        FOREIGN KEY (bag_id) REFERENCES bags(id),
        FOREIGN KEY (sack_id) REFERENCES sacks(id)
    );
    """)

    # --- BATCHES (TEXT PK) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS batches (
        id TEXT PRIMARY KEY,
        weight_mt REAL NOT NULL,
        product_type TEXT CHECK(product_type IN ('butter','liquor','powder')) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # --- BATCH_BAGS (TEXT FKs) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS batch_bags (
        batch_id TEXT,
        bag_id TEXT,
        PRIMARY KEY (batch_id, bag_id),
        FOREIGN KEY (batch_id) REFERENCES batches(id),
        FOREIGN KEY (bag_id) REFERENCES bags(id)
    );
    """)

    # --- Warrant Receipts (TEXT PK) ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS warrant_receipts (
        id TEXT PRIMARY KEY,
        type TEXT CHECK(type IN ('pre-processing','post-processing')) NOT NULL,
        issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        covered_ids TEXT,         -- JSON list of bag_ids or batch_ids
        total_value REAL
    );
    """)

    # LENDERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lenders (
        id TEXT PRIMARY KEY,
        wallet_address TEXT UNIQUE NOT NULL,
        position REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # BUNDLES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bundles (
        id TEXT PRIMARY KEY,
        filter_type TEXT,
        filter_value TEXT,
        interest_rate REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'unfunded', -- Ensure this line exists
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # BUNDLE_SACKS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bundle_sacks (
            bundle_id TEXT,
            sack_id TEXT,
            PRIMARY KEY (bundle_id, sack_id),
            FOREIGN KEY (bundle_id) REFERENCES bundles(id),
            FOREIGN KEY (sack_id) REFERENCES sacks(id)
        );
        """)


    # BUNDLE_LENDERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bundle_lenders (
        bundle_id TEXT,
        lender_id TEXT,
        amount REAL,
        PRIMARY KEY (bundle_id, lender_id),
        FOREIGN KEY (bundle_id) REFERENCES bundles(id),
        FOREIGN KEY (lender_id) REFERENCES lenders(id)
    );
    """)

    # TOKENS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER,
        token_type TEXT CHECK(token_type IN ('internal', 'debt')) NOT NULL,
        amount REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        description TEXT,
        FOREIGN KEY (farmer_id) REFERENCES farmers(id)
    );
    """)

    # TIPS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tips (
        id TEXT PRIMARY KEY,
        farmer_id INTEGER,
        amount REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (farmer_id) REFERENCES farmers(id)
    );
    """)

    # INVOICES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id TEXT PRIMARY KEY,
        amount_paid REAL NOT NULL,
        amount_remaining REAL NOT NULL,
        percent_to_farmers REAL NOT NULL,
        covered_batches TEXT NOT NULL,  -- JSON list of batch_ids
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

def create_farmer(first_name, last_name, email, country, city, gender, phone_number):
    conn = get_connection()
    cursor = conn.cursor()
    farmer_id = generate_id("farmer")
    cursor.execute("""
        INSERT INTO farmers (id, first_name, last_name, email, country, city, gender, phone_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (farmer_id, first_name, last_name, email, country, city, gender, phone_number))
    conn.commit()
    conn.close()

def get_all_farmers():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, first_name, last_name, email, country, city, gender, phone_number, created_at
        FROM farmers
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    conn.close()
    return pd.DataFrame(rows, columns=col_names)

def generate_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex}"


def get_farmer_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, first_name, last_name FROM farmers ORDER BY last_name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [(row[0], f"{row[1]} {row[2]}") for row in rows]


def create_sack_and_mint_token(farmer_id, weight_kg, value_paid, warehouse, delivered_at=None):
    conn = get_connection()
    cursor = conn.cursor()

    sack_id = generate_id("sack")
    if not delivered_at:
        cursor.execute("""
            INSERT INTO sacks (id, farmer_id, weight_kg, value_paid, warehouse, debt_token_minted)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (sack_id, farmer_id, weight_kg, value_paid, warehouse))
    else:
        cursor.execute("""
            INSERT INTO sacks (id, farmer_id, weight_kg, value_paid, delivered_at, warehouse, debt_token_minted)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (sack_id, farmer_id, weight_kg, value_paid, delivered_at, warehouse))

    # Mint a debt token
    cursor.execute("""
        INSERT INTO tokens (farmer_id, token_type, amount, description)
        VALUES (?, 'debt', ?, ?)
    """, (farmer_id, value_paid, f"Debt token minted for sack {sack_id}"))

    conn.commit()
    conn.close()
    return sack_id

def get_sacks_by_farmer(farmer_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, weight_kg, value_paid, warehouse, delivered_at
        FROM sacks
        WHERE farmer_id = ?
        ORDER BY delivered_at DESC
    """, (farmer_id,))
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    conn.close()
    return pd.DataFrame(rows, columns=col_names)


def get_unbagged_sacks():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, f.first_name || ' ' || f.last_name AS farmer_name,
               s.weight_kg, s.value_paid, s.warehouse, s.delivered_at
        FROM sacks s
        JOIN farmers f ON s.farmer_id = f.id
        WHERE s.id NOT IN (SELECT sack_id FROM bag_sacks)
        ORDER BY s.delivered_at ASC
    """)
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    conn.close()
    return pd.DataFrame(rows, columns=col_names)

def create_bag_with_sacks(sack_allocations):
    conn = get_connection()
    cursor = conn.cursor()

    bag_id = generate_id("bag")
    cursor.execute("INSERT INTO bags (id) VALUES (?)", (bag_id,))

    for sack_id, allocated_weight in sack_allocations:
        cursor.execute("""
            INSERT INTO bag_sacks (bag_id, sack_id, allocated_weight_kg)
            VALUES (?, ?, ?)
        """, (bag_id, sack_id, allocated_weight))


    conn.commit()
    conn.close()
    return bag_id

def get_unbagged_sacks_grouped():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.weight_kg, s.warehouse, DATE(s.delivered_at) AS delivery_date
        FROM sacks s
        WHERE s.id NOT IN (SELECT sack_id FROM bag_sacks)
        ORDER BY s.warehouse, delivery_date, delivered_at ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def auto_fill_bags():
    sacks = get_unbagged_sacks_grouped()

    # Group by (warehouse, delivery_date)
    grouped = {}
    for sack_id, weight, warehouse, date in sacks:
        key = (warehouse, date)
        grouped.setdefault(key, []).append((sack_id, weight))

    created_bag_ids = []

    for (warehouse, date), sack_list in grouped.items():
        allocations = []
        current_weight = 0

        for sack_id, weight in sack_list:
            remaining = weight
            while remaining > 0:
                space_left = 63 - current_weight
                if space_left <= 0:
                    if allocations:
                        bag_id = create_bag_with_sacks(allocations)
                        created_bag_ids.append(bag_id)
                    allocations = []
                    current_weight = 0
                    space_left = 63
                portion = min(space_left, remaining)
                allocations.append((sack_id, portion))
                current_weight += portion
                remaining -= portion

        if allocations:
            bag_id = create_bag_with_sacks(allocations)
            created_bag_ids.append(bag_id)

    return created_bag_ids

def get_all_bags():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, created_at
        FROM bags
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_sacks_for_bag(bag_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            s.id AS sack_id,
            f.first_name || ' ' || f.last_name AS farmer_name,
            bs.allocated_weight_kg,
            s.weight_kg AS original_sack_weight,
            s.value_paid AS original_value
        FROM bag_sacks bs
        JOIN sacks s ON bs.sack_id = s.id
        JOIN farmers f ON s.farmer_id = f.id
        WHERE bs.bag_id = ?
    """, (bag_id,))
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    conn.close()

    df = pd.DataFrame(rows, columns=col_names)

    if df.empty:
        return df

    # Avoid divide-by-zero if original weight or total value is 0
    df["allocated_value"] = df.apply(
        lambda row: (row["allocated_weight_kg"] / row["original_sack_weight"] * row["original_value"])
        if row["original_sack_weight"] > 0 else 0,
        axis=1
    )

    total_weight = df["allocated_weight_kg"].sum()
    total_value = df["allocated_value"].sum()

    df["%_weight"] = df["allocated_weight_kg"] / total_weight * 100 if total_weight > 0 else 0
    df["%_value"] = df["allocated_value"] / total_value * 100 if total_value > 0 else 0

    df["%_weight"] = df["%_weight"].round(2)
    df["%_value"] = df["%_value"].round(2)

    return df

def get_unbatched_bags():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
      SELECT b.id,
             SUM(bs.allocated_weight_kg) AS weight_kg,
             b.created_at
      FROM bags b
      LEFT JOIN bag_sacks bs ON b.id = bs.bag_id
      LEFT JOIN batch_bags bb ON b.id = bb.bag_id
      WHERE bb.batch_id IS NULL
      GROUP BY b.id
      ORDER BY b.created_at ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["id","weight_kg","created_at"])

# 2. New: create_batch_with_bags()
def create_batch_with_bags(bag_ids, product_type):
    conn = get_connection()
    cursor = conn.cursor()
    batch_id = generate_id("batch")

    # compute total MT
    df = get_unbatched_bags()
    df_sel = df[df["id"].isin(bag_ids)]
    total_kg = df_sel["weight_kg"].sum()
    weight_mt = total_kg / 1000.0

    cursor.execute("""
      INSERT INTO batches (id, weight_mt, product_type)
      VALUES (?, ?, ?)
    """, (batch_id, weight_mt, product_type))

    for bid in bag_ids:
        cursor.execute("""
          INSERT INTO batch_bags (batch_id, bag_id)
          VALUES (?, ?)
        """, (batch_id, bid))

    conn.commit()
    conn.close()
    return batch_id

# 3. New: get_all_batches()
def get_all_batches():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, weight_mt, product_type, created_at FROM batches ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["id","weight_mt","product_type","created_at"])

# 4. Update: create_warrant_receipt()
def create_warrant_receipt(receipt_type, covered_ids):
    conn = get_connection()
    cursor = conn.cursor()
    receipt_id = generate_id("warrant")

    total_value = 0.0
    if receipt_type == "pre-processing":
        for bag_id in covered_ids:
            df = get_sacks_for_bag(bag_id)
            total_value += df["allocated_value"].sum()
    else:  # post-processing on batches
        for batch_id in covered_ids:
            # sum value across all bags in batch
            cursor.execute("""
              SELECT bs.sack_id
              FROM batch_bags bb
              JOIN bag_sacks bs ON bb.bag_id = bs.bag_id
              WHERE bb.batch_id = ?
            """, (batch_id,))
            sack_ids = [r[0] for r in cursor.fetchall()]
            for sack_id in sack_ids:
                cursor.execute("SELECT weight_kg, value_paid FROM sacks WHERE id = ?", (sack_id,))
                w, v = cursor.fetchone()
                total_value += v  # assume full-value on post
    covered_json = json.dumps(covered_ids)
    cursor.execute("""
      INSERT INTO warrant_receipts (id, type, covered_ids, total_value)
      VALUES (?, ?, ?, ?)
    """, (receipt_id, receipt_type, covered_json, total_value))

    conn.commit()
    conn.close()
    return receipt_id



def get_warrant_receipts_by_type(receipt_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, bags_covered
        FROM warrant_receipts
        WHERE type = ?
    """, (receipt_type,))
    rows = cursor.fetchall()
    conn.close()
    # returns list of (id, bags_covered_json)
    return [{"id": r[0], "bags": json.loads(r[1])} for r in rows]


def auto_fill_batches():
    """
    Groups all unbatched bags into 60 MT batches automatically.
    Any residual (<60 MT) stays unbatched.
    """
    df = get_unbatched_bags()  # returns DataFrame with columns ["id","weight_kg","created_at"]
    # convert to list of (bag_id, weight_kg)
    bag_list = list(df[["id","weight_kg"]].itertuples(index=False, name=None))

    created_batches = []
    current_batch = []
    current_kg = 0

    for bag_id, kg in bag_list:
        # if adding this bag would exceed 60 000 kg, close current batch
        if current_kg + kg > 60000:
            if current_batch:
                batch_id = create_batch_with_bags(current_batch, product_type="liquor")  # or default
                created_batches.append(batch_id)
            current_batch = []
            current_kg = 0
        # if a single bag >60000, put it in its own batch
        if kg > 60000:
            big_batch_id = create_batch_with_bags([(bag_id, kg)], product_type="liquor")
            created_batches.append(big_batch_id)
            continue
        # otherwise add to current
        current_batch.append(bag_id)
        current_kg += kg

    # flush final
    if current_batch:
        batch_id = create_batch_with_bags(current_batch, product_type="liquor")
        created_batches.append(batch_id)

    return created_batches


def get_all_warrant_receipts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, type, issued_at, covered_ids, total_value
        FROM warrant_receipts
        ORDER BY issued_at DESC
    """)
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols)

def get_covered_ids_by_type(receipt_type):
    df = get_all_warrant_receipts()
    df = df[df["type"] == receipt_type]
    covered = []
    for j in df["covered_ids"]:
        covered += json.loads(j)
    return covered


def create_lender(wallet_address, initial_position):
    """Register a new lender with a lending position."""
    conn = get_connection()
    cursor = conn.cursor()
    lender_id = generate_id("lender")
    cursor.execute("""
        INSERT INTO lenders (id, wallet_address, position, created_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (lender_id, wallet_address, initial_position))
    conn.commit()
    conn.close()
    return lender_id

def update_lender_position(lender_id, new_position):
    """Updates the lending position for a given lender."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE lenders SET position = ? WHERE id = ?",
        (new_position, lender_id)
    )
    conn.commit()
    conn.close()


def get_all_lenders():
    """Return a DataFrame of all lenders including their remaining positions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, wallet_address, position, created_at
        FROM lenders
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols)

def get_unfunded_bundles():
    """
    Return a DataFrame of bundles that are still 'unfunded' or 'partially funded',
    along with their total value and current funded amount.
    """
    conn = get_connection()
    # Using pd.read_sql_query for more concise aggregation and DataFrame creation
    df = pd.read_sql_query("""
        SELECT
            b.id,
            b.filter_type,
            b.filter_value,
            b.interest_rate,
            b.status,
            -- Calculate total value of the bundle by summing the value_paid of its constituent sacks
            COALESCE(SUM(s.value_paid), 0) AS total_bundle_value,
            -- Calculate the total amount funded for this bundle
            COALESCE(SUM(bl.amount), 0) AS funded_amount
        FROM bundles b
        JOIN bundle_sacks bs ON b.id = bs.bundle_id -- Join to get sacks in the bundle
        JOIN sacks s ON bs.sack_id = s.id           -- Join to get sack details (value_paid)
        LEFT JOIN bundle_lenders bl ON b.id = bl.bundle_id -- LEFT JOIN to include bundles with no funding yet
        WHERE b.status = 'unfunded' OR b.status = 'partially funded' -- Include both unfunded and partially funded bundles
        GROUP BY b.id, b.filter_type, b.filter_value, b.interest_rate, b.status -- Group by all non-aggregated columns
        ORDER BY b.id
    """, conn)
    conn.close()
    return df


def fund_bundle(lender_id, bundle_id, amount):
    """
    Record a lender’s funding of a bundle, decrement their position,
    and mark the bundle as funded.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # check position
    cursor.execute("SELECT position FROM lenders WHERE id = ?", (lender_id,))
    pos = cursor.fetchone()
    if pos is None:
        conn.close()
        raise ValueError(f"Lender {lender_id} not found")
    if amount > pos[0]:
        conn.close()
        raise ValueError(f"Amount exceeds lender's available position ({pos[0]})")

    # record funding
    cursor.execute("""
        INSERT INTO bundle_lenders (bundle_id, lender_id, amount)
        VALUES (?, ?, ?)
    """, (bundle_id, lender_id, amount))

    # decrement position
    cursor.execute("""
        UPDATE lenders
        SET position = position - ?
        WHERE id = ?
    """, (amount, lender_id))

    # mark bundle funded
    cursor.execute("""
        UPDATE bundles
        SET status = 'funded'
        WHERE id = ?
    """, (bundle_id,))

    conn.commit()
    conn.close()


def get_eligible_sacks_for_bundling(filter_type=None, filter_value=None):
    """
    Returns a DataFrame of unique sack IDs whose bags have a pre‐processing warrant
    and which have not yet been put in any bundle. Optionally filter by a farmer attribute.
    """
    conn = get_connection()
    # 1) Gather all pre‐processing‐covered bag IDs
    cursor = conn.cursor()
    cursor.execute("""
      SELECT covered_ids
      FROM warrant_receipts
      WHERE type='pre-processing';
    """)
    covered = []
    for (j,) in cursor.fetchall():
        covered += json.loads(j)
    covered = list(set(covered))
    if not covered:
        conn.close()
        return pd.DataFrame(columns=["id","farmer_name","weight_kg","value_paid"])

    # 2) Build the SQL with DISTINCT and exclusion of already-bundled sacks
    placeholders = ",".join("?" for _ in covered)
    query = f"""
      SELECT DISTINCT
        s.id AS id,
        f.first_name || ' ' || f.last_name AS farmer_name,
        s.weight_kg,
        s.value_paid,
        f.gender
      FROM bag_sacks bs
      JOIN sacks s   ON bs.sack_id = s.id
      JOIN farmers f ON s.farmer_id = f.id
      WHERE bs.bag_id IN ({placeholders})
        AND s.id NOT IN (
          SELECT sack_id
          FROM bundle_sacks
        )
    """
    params = covered

    # 3) Optionally filter by farmer attribute
    if filter_type and filter_value:
        # Add a check for valid filter_type to prevent SQL injection
        if filter_type in ["country", "city", "gender", "farmer_name"]: # Ensure 'gender' is allowed
            if filter_type == "farmer_name":
                query += " AND (f.first_name || ' ' || f.last_name) LIKE ?"
                params.append(f"%{filter_value}%")
            else:
                query += f" AND f.{filter_type} = ?"
                params.append(filter_value)
        else:
            # Handle invalid filter_type gracefully
            print(f"Warning: Invalid filter_type '{filter_type}' for eligible sacks. Ignoring filter.")
            # You might want to raise an error or return an empty DataFrame here
            # For now, we'll just skip applying this specific filter.

    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    print("Rows fetched:", len(df), "Unique sacks:", df["id"].nunique())
    # df = df.drop_duplicates(subset=["id"])
    # print("Rows fetched after de-dupe:", len(df), "Unique sacks:", df["id"].nunique())
    return df

def create_bundle(filter_type, filter_value, interest_rate, sack_ids):
    """Create a new bundle and attach matched sacks."""
    conn = get_connection()
    cursor = conn.cursor()
    bundle_id = generate_id("bundle")
    cursor.execute("""
      INSERT INTO bundles (id, filter_type, filter_value, interest_rate, status)
      VALUES (?, ?, ?, ?, 'unfunded')
    """, (bundle_id, filter_type, filter_value, interest_rate))
    for sid in sack_ids:
        cursor.execute("""
          INSERT INTO bundle_sacks (bundle_id, sack_id)
          VALUES (?, ?)
        """, (bundle_id, sid))
    conn.commit()
    conn.close()
    return bundle_id


def create_tip(farmer_id, amount, description="Tip"):
    conn = get_connection()
    cursor = conn.cursor()
    tip_id = generate_id("tip")
    cursor.execute("""
      INSERT INTO tips (id, farmer_id, amount, created_at)
      VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (tip_id, farmer_id, amount))
    conn.commit()
    conn.close()
    return tip_id

def get_all_bundles_with_details():
    conn = get_connection()
    cursor = conn.cursor()

    # Get all bundles
    cursor.execute("""
        SELECT
            b.id AS bundle_id,
            b.filter_type,
            b.filter_value,
            b.interest_rate,
            b.status,
            b.created_at
        FROM bundles b
        ORDER BY b.created_at DESC;
    """)
    bundles_raw = cursor.fetchall()
    bundle_cols = [desc[0] for desc in cursor.description]
    df_bundles = pd.DataFrame(bundles_raw, columns=bundle_cols)

    if df_bundles.empty:
        conn.close()
        return pd.DataFrame(columns=[
            'bundle_id', 'filter_type', 'filter_value', 'interest_rate', 'status',
            'created_at', 'total_bundle_value', 'funded_amount', 'calculated_status'
        ])

    # Get sack values for each bundle
    # Join bundles, bundle_sacks, sacks
    cursor.execute("""
        SELECT
            bs.bundle_id,
            s.value_paid,
            s.weight_kg
        FROM bundle_sacks bs
        JOIN sacks s ON bs.sack_id = s.id;
    """)
    sacks_raw = cursor.fetchall()
    sack_cols = [desc[0] for desc in cursor.description]
    df_sacks = pd.DataFrame(sacks_raw, columns=sack_cols)

    # Get funded amounts from bundle_lenders
    cursor.execute("""
        SELECT
            bl.bundle_id,
            SUM(bl.amount) AS funded_amount
        FROM bundle_lenders bl
        GROUP BY bl.bundle_id;
    """)
    lenders_raw = cursor.fetchall()
    lender_cols = [desc[0] for desc in cursor.description]
    df_funded = pd.DataFrame(lenders_raw, columns=lender_cols)


    # Calculate total value of each bundle
    if not df_sacks.empty:
        # Sum value_paid for sacks belonging to each bundle
        bundle_value_sums = df_sacks.groupby('bundle_id')['value_paid'].sum().reset_index()
        bundle_value_sums.rename(columns={'value_paid': 'total_bundle_value'}, inplace=True)
        df_bundles = df_bundles.merge(bundle_value_sums, on='bundle_id', how='left')
    else:
        df_bundles['total_bundle_value'] = 0.0 # Default if no sacks data

    # Merge funded amounts
    if not df_funded.empty:
        df_bundles = df_bundles.merge(df_funded, on='bundle_id', how='left')
    else:
        df_bundles['funded_amount'] = 0.0 # Default if no funding data

    # Fill NaN values with 0.0 for calculations
    df_bundles['total_bundle_value'] = df_bundles['total_bundle_value'].fillna(0.0)
    df_bundles['funded_amount'] = df_bundles['funded_amount'].fillna(0.0)

    # Calculate status based on total_bundle_value and funded_amount
    def calculate_bundle_status(row):
        total = row['total_bundle_value']
        funded = row['funded_amount']

        if total == 0: # Bundle might have no sacks or 0 value sacks
            return 'unfunded' # Or 'empty_bundle' if you want a distinct status
        elif funded >= total:
            return 'funded'
        elif funded > 0 and funded < total:
            return 'partially funded'
        else: # funded is 0 and total > 0
            return 'unfunded'

    df_bundles['calculated_status'] = df_bundles.apply(calculate_bundle_status, axis=1)

    conn.close()
    return df_bundles

def get_all_tokens():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, farmer_id, token_type, amount, created_at, description
        FROM tokens
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols)

def get_token_balance_by_farmer(farmer_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT token_type, SUM(amount) AS balance
        FROM tokens
        WHERE farmer_id = ?
        GROUP BY token_type
    """, (farmer_id,))
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["token_type","balance"])

def mint_internal_tokens(farmer_id, amount, description):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tokens (farmer_id, token_type, amount, description)
        VALUES (?, 'internal', ?, ?)
    """, (farmer_id, amount, description))
    conn.commit()
    conn.close()

def burn_debt_tokens(farmer_id, amount, description):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tokens (farmer_id, token_type, amount, description)
        VALUES (?, 'debt', ?, ?)
    """, (farmer_id, -abs(amount), description))
    conn.commit()
    conn.close()


def burn_internal_tokens(farmer_id, amount, description):
    """
    Inserts a negative‐amount ‘internal’ token to reduce the farmer’s internal balance.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tokens (farmer_id, token_type, amount, description)
        VALUES (?, 'internal', ?, ?)
    """, (farmer_id, -abs(amount), description))
    conn.commit()
    conn.close()

def create_tip(farmer_id, amount, description="Tip"):
    """
    Records a tip and mints the same amount of internal tokens.
    """
    tip_id = generate_id("tip")
    conn = get_connection()
    cursor = conn.cursor()

    # 1) Record tip
    cursor.execute("""
        INSERT INTO tips (id, farmer_id, amount, created_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (tip_id, farmer_id, amount))

    # 2) Mint internal tokens with a descriptive log
    cursor.execute("""
        INSERT INTO tokens (farmer_id, token_type, amount, description)
        VALUES (?, 'internal', ?, ?)
    """, (farmer_id, amount, f"Tip {tip_id}: {description}"))

    conn.commit()
    conn.close()
    return tip_id

def get_all_tips():
    """
    Returns a DataFrame of all tips, with farmer names.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
          t.id,
          t.farmer_id,
          f.first_name || ' ' || f.last_name AS farmer_name,
          t.amount,
          t.created_at
        FROM tips t
        JOIN farmers f ON t.farmer_id = f.id
        ORDER BY t.created_at DESC
    """)
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols)


def get_sacks_for_batch(batch_id):
    """Returns DataFrame with sack_id, farmer_id, farmer_name, allocated_value for a batch."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
          s.id      AS sack_id,
          f.id      AS farmer_id,
          f.first_name || ' ' || f.last_name AS farmer_name,
          bs.allocated_weight_kg,
          (bs.allocated_weight_kg / s.weight_kg) * s.value_paid AS allocated_value
        FROM batch_bags bb
        JOIN bag_sacks bs   ON bb.bag_id = bs.bag_id
        JOIN sacks s        ON bs.sack_id = s.id
        JOIN farmers f      ON s.farmer_id = f.id
        WHERE bb.batch_id = ?
    """, (batch_id,))
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    conn.close()
    df = pd.DataFrame(rows, columns=cols)
    return df


def get_lenders_for_batch(batch_id):
    """
    Returns list of dicts: {
      lender_id, principal_amount, interest_rate
    }
    for all lenders who funded any bundle whose sacks appear in this batch.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
      SELECT DISTINCT bl.lender_id, bl.amount, b.interest_rate
      FROM bundle_lenders bl
      JOIN bundle_sacks bs ON bl.bundle_id = bs.bundle_id
      JOIN batch_bags bb   ON bs.sack_id IN (
         SELECT bs2.sack_id
         FROM batch_bags bb2
         JOIN bag_sacks bs2 ON bb2.bag_id = bs2.bag_id
         WHERE bb2.batch_id = ?
      )
      JOIN bundles b ON bl.bundle_id = b.id
    """, (batch_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"lender_id": r[0], "principal": r[1], "interest_rate": r[2]} for r in rows]


def get_or_create_ecowise_farmer():
    """
    Ensures there is exactly one farmer record named “EcoWise Enterprise”,
    and returns its id.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id
          FROM farmers
         WHERE first_name = 'EcoWise' AND last_name = 'Enterprise'
         LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        eco_id = row[0]
    else:
        eco_id = generate_id("farmer")
        cursor.execute("""
            INSERT INTO farmers (id, first_name, last_name)
            VALUES (?, 'EcoWise', 'Enterprise')
        """, (eco_id,))
        conn.commit()
    conn.close()
    return eco_id


def create_invoice(batch_ids, amount_paid, percent_to_farmers):
    """
    batch_ids: list of batch_id strings
    amount_paid: total invoice amount
    percent_to_farmers: integer 0–100
    """
    eco_id = get_or_create_ecowise_farmer()
    conn = get_connection()
    cursor = conn.cursor()
    invoice_id = generate_id("invoice")

    # 1) Record invoice
    cursor.execute("""
      INSERT INTO invoices
        (id, amount_paid, amount_remaining, percent_to_farmers, covered_batches)
      VALUES (?, ?, ?, ?, ?)
    """, (
      invoice_id,
      amount_paid,
      amount_paid,
      percent_to_farmers / 100.0,
      json.dumps(batch_ids)
    ))
    conn.commit()

    remaining = amount_paid

    # 2) Process each batch in order
    for batch_id in batch_ids:
        if remaining <= 0:
            break

        # -- load all sacks & their allocated_value for this batch
        sacks_df = get_sacks_for_batch(batch_id)
        batch_value = sacks_df["allocated_value"].sum()

        # how much of 'remaining' applies to this batch
        allocate = min(remaining, batch_value)
        remaining -= allocate

        # -- burn debt tokens for farmers pro rata
        for farmer_id, group in sacks_df.groupby("farmer_id"):
            farmer_value = group["allocated_value"].sum()
            burn_amt = allocate * (farmer_value / batch_value)
            cursor.execute("""
              INSERT INTO tokens (farmer_id, token_type, amount, description)
              VALUES (?, 'debt', ?, ?)
            """, (farmer_id, -burn_amt, f"Invoice {invoice_id}: debt burn for batch {batch_id}"))

        # -- repay lenders principal + interest pro rata
        lenders = get_lenders_for_batch(batch_id)
        total_principal = sum(l["principal"] for l in lenders)
        paid_to_lenders = 0.0
        for l in lenders:
            frac = l["principal"] / total_principal
            pay_principal = allocate * frac
            pay_interest  = pay_principal * l["interest_rate"] / 100.0
            pay_total     = pay_principal + pay_interest
            paid_to_lenders += pay_total

            # credit back lender position
            cursor.execute("""
              UPDATE lenders
              SET position = position + ?
              WHERE id = ?
            """, (pay_total, l["lender_id"]))

        # -- mark related bundles as paid
        cursor.execute("""
          UPDATE bundles
          SET status = 'paid'
          WHERE id IN (
            SELECT DISTINCT bs.bundle_id
            FROM bundle_sacks bs
            JOIN batch_bags bb ON bs.sack_id IN (
              SELECT bs2.sack_id
              FROM batch_bags bb2
              JOIN bag_sacks bs2 ON bb2.bag_id = bs2.bag_id
              WHERE bb2.batch_id = ?
            )
          )
        """, (batch_id,))

        # -- allocate remainder
        remainder_after_lenders = allocate - paid_to_lenders
        if remainder_after_lenders < 0:
            remainder_after_lenders = 0

        to_farmers = remainder_after_lenders * (percent_to_farmers / 100.0)
        to_ecowise = remainder_after_lenders - to_farmers

        # a) credit farmers pro rata if there's anything left
        if to_farmers > 0:
            for farmer_id, group in sacks_df.groupby("farmer_id"):
                farmer_value = group["allocated_value"].sum()
                fam_amt = to_farmers * (farmer_value / batch_value)
                cursor.execute("""
                  INSERT INTO tokens (farmer_id, token_type, amount, description)
                  VALUES (?, 'internal', ?, ?)
                """, (
                    farmer_id,
                    fam_amt,
                    f"Invoice {invoice_id}: bonus for batch {batch_id}"
                ))

        # b) credit EcoWise only if there's remainder
        if to_ecowise > 0:
            cursor.execute("""
              INSERT INTO tokens (farmer_id, token_type, amount, description)
              VALUES (?, 'internal', ?, ?)
            """, (
                eco_id,
                to_ecowise,
                f"Invoice {invoice_id}: EcoWise remainder for batch {batch_id}"
            ))

        conn.commit()

    conn.close()
    return invoice_id

def get_all_invoices():
    """
    Returns a DataFrame of all invoices.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            id,
            amount_paid,
            amount_remaining,
            percent_to_farmers,
            covered_batches,
            created_at
        FROM invoices
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols)


def get_sack_ownership(sack_id):
    """
    Returns the farmer who delivered this sack plus the sack’s weight, original value, and delivery time.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            f.first_name || ' ' || f.last_name AS farmer_name,
            f.id               AS farmer_id,
            s.weight_kg,       -- ADDED LINES START HERE
            s.value_paid,      -- ADDED LINES STOP HERE
            s.delivered_at     -- ADDED LINES START HERE
        FROM sacks s
        JOIN farmers f ON s.farmer_id = f.id
        WHERE s.id = ?
    """, (sack_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "farmer_name":  row[0],
            "farmer_id":    row[1],
            "weight_kg":    row[2],  # ADDED LINES START HERE
            "value_paid":   row[3],  # ADDED LINES STOP HERE
            "delivered_at": row[4]   # ADDED LINES START HERE
        }
    return None

def get_bags_for_sack(sack_id):
    """
    Returns a DataFrame of all bags that include this sack.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.id AS bag_id,
               b.created_at,
               bs.allocated_weight_kg
          FROM bag_sacks bs
          JOIN bags b ON bs.bag_id = b.id
         WHERE bs.sack_id = ?
         ORDER BY b.created_at
    """, (sack_id,))
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["bag_id","created_at","allocated_weight_kg"])

def get_batches_for_sack(sack_id):
    """
    Returns a DataFrame of all distinct batches (60MT) that include any bag containing this sack.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT              -- ADDED LINES START HERE
               bat.id            AS batch_id,
               bat.product_type,
               bat.weight_mt,
               bat.created_at
          FROM batch_bags bb
          JOIN batches bat ON bb.batch_id = bat.id
         WHERE bb.bag_id IN (
             SELECT bs.bag_id
               FROM bag_sacks bs
              WHERE bs.sack_id = ?
         )
      ORDER BY bat.created_at       -- ADDED LINES STOP HERE
    """, (sack_id,))
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["batch_id","product_type","weight_mt","created_at"])

def get_bundles_for_sack(sack_id):
    """
    Returns a DataFrame of all distinct financing bundles that include this sack.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT              -- ADDED LINES START HERE
               bnd.id           AS bundle_id,
               bnd.filter_type,
               bnd.filter_value,
               bnd.interest_rate,
               bnd.status
          FROM bundle_sacks bs
          JOIN bundles bnd ON bs.bundle_id = bnd.id
         WHERE bs.sack_id = ?
    """, (sack_id,))
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=[
        "bundle_id","filter_type","filter_value","interest_rate","status"
    ])  # ADDED LINES STOP HERE


def get_all_sack_ids():
    """
    Returns a list of every sack ID in the system, most recent first.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sacks ORDER BY delivered_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]