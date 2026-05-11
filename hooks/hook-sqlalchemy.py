from PyInstaller.utils.hooks import collect_submodules


# Project này dùng URL mysql+pymysql://..., nên bản exe bắt buộc phải mang theo
# dialect MySQL của SQLAlchemy thay vì chỉ mỗi package pymysql.
hiddenimports = [
    "sqlalchemy",
    "sqlalchemy.orm",
    "sqlalchemy.ext.declarative",
    "sqlalchemy.sql.default_comparator",
    "sqlalchemy.dialects",
    "sqlalchemy.dialects.mysql",
    "sqlalchemy.dialects.mysql.base",
    "sqlalchemy.dialects.mysql.mysqldb",
    "sqlalchemy.dialects.mysql.pymysql",
    "pymysql",
    "PyQt5.sip",
]

hiddenimports += collect_submodules("sqlalchemy.dialects.mysql")
