"""Run: python src/classify_fmcg.py --data data/raw/complete_journey --out results"""
import argparse, hashlib, json
from pathlib import Path
import pandas as pd
import pyreadr

IN = {'GROCERY','FROZEN GROCERY','PRODUCE','MEAT','MEAT-PCKGD','SEAFOOD','SEAFOOD-PCKGD','DELI','PASTRY'}
OUT = {'FUEL','FLORAL','GARDEN CENTER','RESTAURANT','TRAVEL & LEISURE','PHOTO & VIDEO','TOYS','POSTAL CENTER','AUTOMOTIVE','ELECT &PLUMBING','HOUSEWARES','CNTRL/STORE SUP','CHARITABLE CONT','GM MERCH EXP','COUPON','SPIRITS'}
# Exact observed categories requiring review, never fuzzy keyword matching.
REVIEW_CATEGORY = {'COUPON/MISC ITEMS','COUPON','BOTTLE DEPOSITS','DELI SUPPLIES','MEAT SUPPLIES','PROD SUPPLIES','PET CARE SUPPLIES','MISCELLANEOUS','MEAT - MISC','SEAFOOD - MISC','PKG.SEAFOOD MISC','SEASONAL','LIQUOR','BEERS/ALES','DOMESTIC WINE','MISC WINE','IMPORTED WINE'}
VERSION = '1.3-cosmetics-and-exclusions'

# Các type đã xem xét, chỉ áp dụng trong department DRUG GM.
PERSONAL_CARE_TYPES = {
    "SOAP - LIQUID & BAR": {
        "BAR SOAP",
        "BODY WASH",
        "LIQUID SOAP",
        "SOAP- LIQ&BAR",
        "BATH BUBBLES-BATH SOAPS-ADDITI",
        "FACIAL SOAPS-SCRUBS-MASKS",
        "FRAGRANCED BATH PRODUCTS",
    },
    "HAIR CARE PRODUCTS": {
        "SHAMPOO",
        "HAIR CONDITIONERS AND RINSES",
        "HAIR COLOR AND DEVELOPERS",
        "HAIR PERMANENTS AND RELAXERS",
        "HAIR SETS AND GELS",
        "WOMENS  HAIR SPRAYS",
    },
    "ORAL HYGIENE PRODUCTS": {
        "TOOTHPASTE",
        "MOUTHWASH RINSES AND SPRAYS",
        "MOUTHWASHES (ANTISEPTIC)",
        "DENTURE ADHESIVES",
        "DENTURE CLEANSERS",
    },
    "DEODORANTS": {
        "AEROSOL DEODORANTS",
        "ANTIPERSPIRANTS ONLY (AEROSOL)",
        "ANTIPERSPIRANTS ONLY (ALL OTHE",
        "DEODORANTS",
        "N/A DEOD SPRAY/GEL DEOD",
        "ROLL-ON DEODORANTS",
        "SOLID/STK DEODORANTS",
    },
    "DIAPERS & DISPOSABLES": {
        "BABY DIAPERS",
    },
    "FEMININE HYGIENE": {
        "FEM. HYGN. TAMPONS",
        "FEM. HYGN.NAPKINS",
        "FEM. HYGN. DEODORANTS",
        "FEM HYGN DOUCHES",
    },
}
NUTRITION_TYPES = {
    "BABYFOOD": {
        "BABY CEREAL", "BABY CRACKERS", "BABY FOOD", "BABY JUICES",
    },
    "BAKING": {
        "CEREAL - HOT", "DRESSINGS", "FLOURS/GRAINS/SUGAR",
        "MEATLESS/VEGETARIAN", "MIXES", "SPICES",
    },
    "BEVERAGE": {
        "ASEPTIC MILK", "CAN/BTL BEVERAGE", "ENERGY DRINK",
        "INSTANT TEA & TEA MIX (W/SUGAR",
        "TEA (CANNED/BOTTLED) W/SWEETEN",
        "TEA BAGS HERBAL & FLAVORED", "TEA DRY",
        "TEA SWEETENED", "TEA UNSWEETENED (CAN/BOTTLE)",
    },
    "BREAD": {
        "MEXICAN SOFT TORTILLAS AND WRA",
    },
    "BULK FOODS": {
        "NUTS",
    },
    "CEREAL/BREAKFAST": {
        "BABY CEREAL", "BREAKFAST BARS/TARTS/SCONES",
        "CEREAL - COLD", "CEREAL - HOT",
        "DIET CNTRL BARS NUTRITIONAL", "GRANOLA",
    },
    "CHIPS&SNACKS": {
        "CANDY W/O FLOUR", "DRIED FRUIT - OTHER",
        "GOURMET CHIPS (TERRA)", "POPCORN", "POTATO CHIPS",
        "PRETZELS", "RICE CAKES", "SPECIALTY CHIPS (SOY CRISPS/PI",
        "SPECIALTY SNACKS (SOYNUTS/TRAI", "TORTILLA CHIPS",
    },
    "CONDIMENTS": {
        "CARIBBEAN FOODS", "CATSUP", "DRESSINGS",
        "FLOURS/GRAINS/SUGAR", "HONEY/SYRUP",
        "JELLIES/PRESERVES/APPLE BUTTER",
        "KETCHUP/MUSTARD/BBQ SCE/MARINA",
        "NUT BUTTERS/PEANUT BUTTER", "OILS/VINEGAR",
        "ORIENTAL OTHER SAUCES MARINAD",
        "SALSA/DIPS", "SPICES & SEASONINGS",
    },
    "DRIED FRUIT": {
        "CANDY BAGS-NON CHOCOLATE", "DATES", "DRIED FRUIT",
        "DRIED FRUIT - OTHER", "DRIED PLUMS",
        "ORGANIC DRIED FRUIT", "RAISINS",
    },
    "DRY TEA/COFFEE/COCO MIX": {
        "COFFEE GROUND", "COFFEE WHOLE BEAN", "REGULAR BEAN",
        "TEA BAGS HERBAL & FLAVORED", "TEA DRY",
    },
    "FITNESS&DIET": {
        "BARS - GRANOLA/SNACK", "BREAKFAST BARS/TARTS/SCONES",
        "DIET CNTRL BARS NUTRITIONAL",
        "FITNESS&DIET - BARS", "FITNESS&DIET ISOTONIC DRINKS",
        "YOGURT",
    },
    "FROZEN": {
        "FROZEN BREAD", "FROZEN BREAKFAST", "FROZEN BURGERS",
        "FROZEN CONVENIENCE/POCKETS",
        "FROZEN DESSERT (ICE CREAM CAKE",
        "FROZEN ENTREES", "FROZEN FRUIT", "FROZEN ICE CREAM",
        "FROZEN MEAL COMBO/DINNERS", "FROZEN MEAT",
        "FROZEN MEAT (VEGETARIAN)", "FROZEN PIZZA",
        "FROZEN SIDE DISH (MAC&CHS)", "FROZEN VEGETABLES",
        "FRZN MEAT ALTERNATIVES", "ROLLS: BAGELS",
        "VEGETARIAN MEATS",
    },
    "JUICE": {
        "BLENDED JUICE&COMBINATIONS (OV",
        "DRINKS - CARB JUICE (OVER 50%", "JUICE",
        "JUICE (100% JUICE)", "JUICE (OVER 50% JUICE)",
        "JUICE (UNDER 10% JUICE)", "NON-CARB JCE (UNDER 50%JCE)",
        "NON-CARB JCE(OVER 50% JCE)", "TEA SWEETENED",
        "UNIQUE SODAS",
    },
    "NDAIRY/TEAS/JUICE/SOD": {
        "COFF SHOP: RETAIL PACK BEVERAG",
        "JUICE (UNDER 10% JUICE)",
    },
    "NON-DAIRY BEVERAGES": {
        "DRINKS - CARB JUICE (OVER 50%",
        "RICE BEVERAGE", "SOY BEVERAGE", "SOY/RICE MILK",
    },
    "ORGANICS FRUIT & VEGETABLES": {
        "ORGANIC DRIED FRUIT",
    },
    "PACKAGED NATURAL SNACKS": {
        "CANDY", "DRIED FRUIT", "DRIED FRUIT - OTHER",
        "NUTS", "NUTS OTHER", "PRETZELS", "TRAIL MIXES",
    },
    "PREPARED/PKGD FOODS": {
        "APPLE SAUCE/PUDDING", "BOXED PREPARED/ENTREE/DRY PREP",
        "CANNED FRUIT", "GRAINS", "KETCHUP/MUSTARD/BBQ SCE/MARINA",
        "MEAT - CAN/POUCH", "MEATLESS/VEGETARIAN",
        "MISC CND MEATS", "PASTA/RAMEN", "SAUCES",
        "TOFU", "VEGETABLES/DRY BEANS",
    },
    "REFRIGERATED": {
        "ASEPTIC MILK", "BUTTER", "CHEESE SPREADS", "DAIRY CHEESE",
        "EGGS", "FLUID MILK", "JUICE", "JUICE (OVER 50% JUICE)",
        "JUICE (UNDER 10% JUICE)", "JUICE (UNDER 50% JUICE)",
        "KEFIR", "NON-DAIRY CHEESE", "NUT REFRIG JUICE OVER 50%",
        "SOUR CREAM/COTTAGE CHEESE", "SOY/RICE MILK",
        "TEA SWEETENED", "TOFU", "VEGETARIAN MEATS", "YOGURT",
    },
    "RICE CAKES": {
        "LARGE - RICE CAKES", "POPCORN - MICROWAVE", "RICE CAKES",
    },
    "SNKS/CKYS/CRKR/CNDY": {
        "BABY CRACKERS", "BARS - GRANOLA/SNACK",
        "BREAKFAST BARS/TARTS/SCONES", "CANDY/CHOCOLATE",
        "COOKIES/SWEET GOODS", "CRACKERS",
        "DIET CNTRL BARS NUTRITIONAL", "HONEY/SYRUP", "RAISINS",
        "SPECIALTY CHIPS (SOY CRISPS/PI",
        "SPECIALTY SNACKS (SOYNUTS/TRAI",
    },
    "SOUP": {
        "ASCEPTIC", "BROTHS", "CANS SOUP/CHILI", "CUPS", "DRY",
    },
    "WATER": {
        "FORTIFIED/ENERGY WATER", "JUICE", "JUICE (100% JUICE)",
        "NON-CARB WATER FLVR - DRNK/MNR", "SPRING WATER",
    },
}
COSMETICS_TYPES = {
    "BATH": {
        "BATH BEADS",
        "BATH BUBBLES-BATH SOAPS-ADDITI",
        "BATH OILS",
        "BODY WASH",
        "DIPILATORIES",
        "FACIAL SOAPS-SCRUBS-MASKS",
        "FRAGRANCED BATH PRODUCTS",
        "HAND AND BODY CREAM",
        "LOTIONS/CREAMS/OILS",
        "SOAP- LIQ&BAR",
        "SUNTAN PROD W/SPF LOTION/OIL",
    },
    "MAKEUP AND TREATMENT": {
        "FACE MAKE UP AND TREATMENT",
        "FACIAL MOISTURIZERS",
        "FACIAL SOAPS-SCRUBS-MASKS",
        "FRAGRANCED BATH PRODUCTS",
        "SUNTAN PROD W/SPF LOTION/OIL",
    },
    "FRAGRANCES": {
        "COTY FRAGRANCES",
        "DESIGNER FRAGRANCES",
        "NEW DESIGNER FRAGRANCE",
        "REVLON FRAGRANCES",
        "FRAGRANCED BATH PRODUCTS",
    },
}

# Khóa là (department, category), giá trị là các type ngoài phạm vi.
EXCLUDED_TYPES = {
    ("COSMETICS", "COSMETIC ACCESSORIES"): {
        "BANDANA/SCARVES",
        "COSMETIC BAGS",
        "CURFEW JEWELRY",
        "GADGETS/TOOLS",
        "IMPLEMENTS SETS",
        "JEWELRY/COSTUME FAF",
        "JEWELRY/COSTUME HOLIDAY",
        "JEWELRY/COSTUME NECK/BRAC ANK",
        "SMALL ACCESS COLD WEATHER",
        "SMALL ACCESS UMBRELLAS",
        "SUNGLASSES SOLARGENICS",
    },
    ("COSMETICS", "MAKEUP AND TREATMENT"): {
        "IMPLEMENTS SETS",
    },
    ("DRUG GM", "PERSONAL CARE APPLIANCES"): {
        "HAIR DRYERS STYLERS SETTER",
        "PERSNL APPL: FT BTH/MASSGRS",
        "SHAVERS: MENS  WOMENS",
    },
    ("DRUG GM", "PORTABLE ELECTRIC APPLIANCES"): {
        "BLEND/MIX",
        "CAN OPENERS",
        "FOOD SAVERS",
        "IRONS",
        "TOAST/GRIDDLES",
    },
    ("DRUG GM", "PREPAID WIRELESS&ACCESSORIES"): {
        "CELLULAR ACCESSORIES",
        "MMK DOWNLOAD",
        "PREPAID WIRELESS CARDS",
        "WIRELESS PHONES",
    },
    ("DRUG GM", "IN-STORE PHOTOFINISHING"): {
        "DEVELOP/ PRINT PROCESSING",
        "KODAK COPY PRINT STATION",
        "ONE HOUR PROCESSING",
        "OVERNIGHT PROCESSING",
    },
    ("DRUG GM", "OVERNIGHT PHOTOFINISHING"): {
        "ONE HOUR PROCESSING",
        "OVERNIGHT PROCESSING",
    },
    ("DRUG GM", "TICKETS"): {
        "TICKETS",
    },
}
def read(path):
    return next(iter(pyreadr.read_r(str(path)).values()))

def main():
    a=argparse.ArgumentParser(); a.add_argument('--data',required=True);a.add_argument('--out',default='results');a=a.parse_args()
    data=Path(a.data);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    p=read(data/'products.rda');t=read(data/'transactions.rds')
    for d in (p,t): d['product_id']=d.product_id.astype('string')
    assert p.product_id.notna().all() and p.product_id.is_unique
    n=p[['department','product_category','product_type']].astype('string').apply(lambda c:c.str.strip().str.upper())
    p['scope_status']='REVIEW';p['scope_reason']='Mixed or unconfirmed department'
    m=n.department.isin(OUT);p.loc[m,['scope_status','scope_reason']]=['OUT_OF_SCOPE','Department excluded by project scope v1']
    m=n.department.isin(IN)&n.notna().all(axis=1)&n.ne('').all(axis=1)
    p.loc[m,['scope_status','scope_reason']]=['IN_SCOPE','Eligible department with category and type']
    m=n.department.isin(IN)&n.product_category.isin(REVIEW_CATEGORY)
    p.loc[m,['scope_status','scope_reason']]=['REVIEW','Exact category requires scope review']
    m=n.department.isin(IN)&(n.isna().any(axis=1)|n.eq('').any(axis=1))
    p.loc[m,['scope_status','scope_reason']]=['REVIEW','Missing classification attribute']
    # Bổ sung quy tắc chi tiết cho các sản phẩm đang REVIEW.
    for category, product_types in PERSONAL_CARE_TYPES.items():
        mask = (
            p["scope_status"].eq("REVIEW")
            & n["department"].eq("DRUG GM")
            & n["product_category"].eq(category)
            & n["product_type"].isin(product_types)
        ).fillna(False)

        p.loc[mask, "scope_status"] = "IN_SCOPE"
        p.loc[mask, "scope_reason"] = (
            "Reviewed personal-care category/type"
        )
    # Bổ sung thực phẩm và đồ uống thuộc NUTRITION.
    for category, product_types in NUTRITION_TYPES.items():
        mask = (
            p["scope_status"].eq("REVIEW")
            & n["department"].eq("NUTRITION")
            & n["product_category"].eq(category)
            & n["product_type"].isin(product_types)
        ).fillna(False)

        p.loc[mask, "scope_status"] = "IN_SCOPE"
        p.loc[mask, "scope_reason"] = (
            "Reviewed nutrition food/beverage category/type"
        )
        # Bổ sung mỹ phẩm tiêu hao.
    for category, product_types in COSMETICS_TYPES.items():
        mask = (
            p["scope_status"].eq("REVIEW")
            & n["department"].eq("COSMETICS")
            & n["product_category"].eq(category)
            & n["product_type"].isin(product_types)
        ).fillna(False)

        p.loc[mask, "scope_status"] = "IN_SCOPE"
        p.loc[mask, "scope_reason"] = (
            "Reviewed consumable cosmetics category/type"
        )

    # Loại dụng cụ lâu bền và dịch vụ đã xác định.
    for (department, category), product_types in EXCLUDED_TYPES.items():
        mask = (
            p["scope_status"].eq("REVIEW")
            & n["department"].eq(department)
            & n["product_category"].eq(category)
            & n["product_type"].isin(product_types)
        ).fillna(False)

        p.loc[mask, "scope_status"] = "OUT_OF_SCOPE"
        p.loc[mask, "scope_reason"] = (
            "Reviewed durable goods/accessories or services"
        )
    p['scope_rule_version']=VERSION
    # Missing products receive a distinct decision for each source ID.
    missing=sorted(set(t.product_id)-set(p.product_id))
    extra=pd.DataFrame({'product_id':missing,'scope_status':'REVIEW','scope_reason':'Product missing from lookup','scope_rule_version':VERSION})
    decisions=pd.concat([p,extra],ignore_index=True)
    joined=t.merge(decisions[['product_id','scope_status']],on='product_id',how='left',validate='many_to_one')
    assert len(joined)==len(t) and joined.scope_status.notna().all()
    # Source monetary values have cents; use integer cents for reconciliation.
    cents=t.sales_value.mul(100).round().astype('int64')
    assert (t.sales_value.mul(100)-cents).abs().max()<1e-6
    joined['sales_cents']=cents.to_numpy()
    summary=joined.groupby('scope_status').agg(transaction_rows=('product_id','size'),transacting_products=('product_id','nunique'),sales_cents=('sales_cents','sum'),baskets=('basket_id','nunique'),households=('household_id','nunique'))
    summary['lookup_products']=p.groupby('scope_status').size()
    summary['sales_value']=summary.sales_cents/100
    summary['transaction_pct']=summary.transaction_rows/len(t)*100
    summary['sales_pct']=summary.sales_cents/cents.sum()*100
    assert summary.transaction_rows.sum()==len(t) and summary.sales_cents.sum()==cents.sum()
    decisions.to_csv(out/'product_scope.csv',index=False)
    summary.to_csv(out/'scope_summary.csv')
    p.groupby(['department','scope_status'],dropna=False).size().rename('products').to_csv(out/'department_summary.csv')
    p[p.scope_status.eq('REVIEW')].groupby(['department','product_category','product_type','scope_reason'],dropna=False).size().rename('products').to_csv(out/'review_categories.csv')
    manifest={'rule_version':VERSION,'source_rows':len(t),'lookup_products':len(p),'missing_lookup_products':len(missing),'source_sales_cents':int(cents.sum()),'row_reconciliation':'PASS','sales_reconciliation':'PASS','sources':{f:hashlib.sha256((data/f).read_bytes()).hexdigest() for f in ['products.rda','transactions.rds']}}
    (out/'validation.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print(summary.to_string());print(json.dumps(manifest))
if __name__=='__main__': main()
