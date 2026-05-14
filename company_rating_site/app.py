from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:Xleboytki2@localhost:5433/agro_rating')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def format_number(value):
    if value is None or value == 0 or value == "0":
        return "0"
    try:
        if isinstance(value, str):
            value = float(value) if '.' in value else int(value)
        return f"{int(value):,}".replace(",", " ")
    except:
        return str(value)

def get_company_info(inn):
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT * FROM companies WHERE inn = :inn"),
            {"inn": str(inn)}
        )
        company = result.fetchone()
        if not company:
            return None
        
        company_dict = dict(company._mapping)
        
        fin_result = db.execute(
            text("SELECT * FROM finances WHERE inn = :inn ORDER BY year DESC"),
            {"inn": str(inn)}
        )
        finances = [dict(row._mapping) for row in fin_result.fetchall()]
        last_finance = finances[0] if finances else {}
        
        rating_value = float(company_dict.get("rating", 0)) if company_dict.get("rating") else 0
        org_type = company_dict.get("type", "ЮЛ") if company_dict.get("type") else "ЮЛ"
        
        info = {
            "inn": str(company_dict.get("inn", "Н/Д")),
            "rating": rating_value,
            "category": str(company_dict.get("category", "Н/Д")),
            "type": org_type,
            "name": str(company_dict.get("name", "Н/Д")),
            "ogrn": str(company_dict.get("ogrn", "Н/Д")),
            "code": str(company_dict.get("okved_code", "Н/Д")),
            "region": str(company_dict.get("region", "Н/Д")),
            "director": str(company_dict.get("director", "Н/Д")),
            "reg_date": str(company_dict.get("reg_date", "Н/Д")),
            "status": str(company_dict.get("status", "Н/Д")),
            "capital": format_number(company_dict.get("authorized_capital", 0)),
            "debts": format_number(company_dict.get("debts", 0)),
            "plaintiff": format_number(company_dict.get("plaintiff", 0)),
            "defendant": format_number(company_dict.get("defendant", 0)),
            "finance_status": "Данные найдены" if finances else "Финансовые данные отсутствуют",
            "last_revenue": format_number(last_finance.get("revenue", 0)),
            "last_profit": format_number(last_finance.get("profit", 0)),
            "last_balance": format_number(last_finance.get("balance", 0)),
            # Нормализованные показатели для экспертной оценки
            "rev_norm": float(company_dict.get("rev_norm", 0)) if company_dict.get("rev_norm") else 0,
            "profit_norm": float(company_dict.get("profit_norm", 0)) if company_dict.get("profit_norm") else 0,
            "balance_norm": float(company_dict.get("balance_norm", 0)) if company_dict.get("balance_norm") else 0,
            "capital_norm": float(company_dict.get("capital_norm", 0)) if company_dict.get("capital_norm") else 0,
            "growth_norm": float(company_dict.get("growth_norm", 0)) if company_dict.get("growth_norm") else 0,
            "debts_norm": float(company_dict.get("debts_norm", 0)) if company_dict.get("debts_norm") else 0,
            "courts_norm": float(company_dict.get("courts_norm", 0)) if company_dict.get("courts_norm") else 0
        }
        
        fin_by_year = []
        for fin in finances:
            fin_by_year.append({
                "year": int(fin.get("year", 0)),
                "revenue": format_number(fin.get("revenue", 0)),
                "profit": format_number(fin.get("profit", 0)),
                "balance": format_number(fin.get("balance", 0))
            })
        info["fin_by_year"] = fin_by_year
        
        category_colors = {
            "Надёжный": "#28a745",
            "Умеренный риск": "#ffc107",
            "Рискованный": "#fd7e14",
            "Высокий риск": "#dc3545"
        }
        info["category_color"] = category_colors.get(info["category"], "#6c757d")
        
        return info
    except Exception as e:
        print(f"Ошибка: {e}")
        return None
    finally:
        db.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['GET'])
def search():
    inn = request.args.get('inn', '').strip()
    if not inn:
        return jsonify({"error": "Введите ИНН"}), 400
    if not inn.isdigit():
        return jsonify({"error": "ИНН должен содержать только цифры"}), 400
    if len(inn) not in [10, 12]:
        return jsonify({"error": "ИНН должен содержать 10 или 12 цифр"}), 400
    
    company = get_company_info(inn)
    if company is None:
        return jsonify({"error": f"Компания с ИНН {inn} не найдена"}), 404
    return jsonify(company)

@app.route('/suggest', methods=['GET'])
def suggest():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 3:
        return jsonify([])
    
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT inn, name, category FROM companies WHERE inn LIKE :query LIMIT 10"),
            {"query": f"{query}%"}
        )
        suggestions = [{"inn": str(row[0]), "name": str(row[1]) if row[1] else "Н/Д", 
                       "category": str(row[2]) if row[2] else "Н/Д"} for row in result.fetchall()]
        return jsonify(suggestions)
    except Exception as e:
        return jsonify([])
    finally:
        db.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
