# main.py
import pandas as pd


def load_and_prepare(path: str) -> pd.DataFrame:
    """
    Загружает данные и подготавливает их для анализа и визуализации.
    (Функция встроена в main.py)
    """
    df = pd.read_csv(path)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    numeric_cols = [
        "Price", "Rooms", "Bedroom2", "Bathroom",
        "Car", "Landsize", "BuildingArea",
        "YearBuilt", "Propertycount"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    cat_cols = ["CouncilArea", "Regionname", "Suburb", "Type"]
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown")

    if "Date" in df.columns:
        df["SaleYear"] = df["Date"].dt.year
        df["SaleMonth"] = df["Date"].dt.month

    if "YearBuilt" in df.columns:
        current_year = pd.Timestamp.now().year
        df["HouseAge"] = current_year - df["YearBuilt"]
        df["IsOldHouse"] = (df["HouseAge"] > 50).astype(int)

    if "Rooms" in df.columns and "Price" in df.columns:
        rooms = df["Rooms"].where(df["Rooms"] > 0)
        df["PricePerRoom"] = df["Price"] / rooms

    if "Landsize" in df.columns and "BuildingArea" in df.columns:
        land = df["Landsize"].where(df["Landsize"] > 0)
        df["BuildRatio"] = df["BuildingArea"] / land

    if "Propertycount" in df.columns and "Landsize" in df.columns:
        land = df["Landsize"].where(df["Landsize"] > 0)
        df["Density"] = df["Propertycount"] / land

    return df


# функция для квадратных метров
def add_price_ppm2(
    df: pd.DataFrame,
    area_col: str = "BuildingArea",
    back_area_col: str = "Landsize",
    out_col: str = "PricePerM2"
) -> pd.DataFrame:
    if "Price" not in df.columns:
        raise ValueError("Column 'Price' not found in DataFrame")

    d = df.copy()

    d["Price"] = pd.to_numeric(d["Price"], errors="coerce")
    if area_col in d.columns:
        d[area_col] = pd.to_numeric(d[area_col], errors="coerce")
    if back_area_col in d.columns:
        d[back_area_col] = pd.to_numeric(d[back_area_col], errors="coerce")

    area = d[area_col].where(d[area_col] > 0) if area_col in d.columns else pd.Series(index=d.index, dtype="float64")
    fallback = d[back_area_col].where(d[back_area_col] > 0) if back_area_col in d.columns else pd.Series(index=d.index, dtype="float64")

    ppm2 = d["Price"] / area
    ppm2 = ppm2.where(ppm2.notna(), d["Price"] / fallback)

    d[out_col] = ppm2
    return d


# функция для таблицы подсчета через PricePerM2 для разных регионов и тд
def summarize_market(
    df: pd.DataFrame,
    group_level: str = "Regionname",
    metric: str = "PricePerM2",
    top_n: int = 15
) -> pd.DataFrame:
    allowed = {"Regionname", "CouncilArea", "Suburb"}
    if group_level not in allowed:
        raise ValueError(f"group_level must be one of {sorted(allowed)}")

    if metric not in df.columns:
        raise ValueError(f"metric '{metric}' not found in df.columns")

    d = df.dropna(subset=[group_level, metric]).copy()

    out = (
        d.groupby(group_level)[metric]
        .agg(count="count", mean="mean", median="median", min="min", max="max")
        .sort_values("median", ascending=False)
    )

    if top_n:
        out = out.head(top_n)

    return out.reset_index()


# ---- ЕДИНАЯ ТОЧКА ВХОДА ----
df = load_and_prepare(r"melb_data.csv")
print(df)

df2 = add_price_ppm2(df)

# можно выбирать по чему делать расчет
region_tbl = summarize_market(df2, group_level="Regionname", metric="PricePerM2", top_n=None)
council_tbl = summarize_market(df2, group_level="CouncilArea", metric="PricePerM2", top_n=20)
suburb_tbl = summarize_market(df2, group_level="Suburb", metric="PricePerM2", top_n=20)

# создаём папку output/ без "import os"
try:
    __import__("os").makedirs("output", exist_ok=True)
except Exception:
    pass

# сохраняем CSV (теперь всегда пытаемся в output/)
try:
    region_tbl.to_csv("output/summary_regionname.csv", index=False)
    council_tbl.to_csv("output/summary_councilarea_top20.csv", index=False)
    suburb_tbl.to_csv("output/summary_suburb_top20.csv", index=False)
except Exception:
    # запасной вариант: сохраняем рядом с main.py
    region_tbl.to_csv("summary_regionname.csv", index=False)
    council_tbl.to_csv("summary_councilarea_top20.csv", index=False)
    suburb_tbl.to_csv("summary_suburb_top20.csv", index=False)

# если есть visualization_advanced.py + зависимости, делаем HTML-отчет
try:
    from visualization_advanced import export_analysis_report
    export_analysis_report(
        df2,
        output_dir="output",
        price_column="Price",
        district_column="Suburb",
        category_column="Type"
    )
except Exception:
    pass

print(df2)
