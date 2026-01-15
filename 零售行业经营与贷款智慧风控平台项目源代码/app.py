# ==================== 导入模块 ====================
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import numpy as np
import os
import csv
import io

# ==================== Flask应用配置 ====================
app = Flask(__name__)
# 安全密钥：用于会话加密，生产环境应更改为随机字符串
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
# 数据库配置：使用SQLite数据库
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'retail_platform.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ==================== 数据库和认证初始化 ====================
db = SQLAlchemy(app)  # 初始化SQLAlchemy ORM
login_manager = LoginManager(app)  # 初始化Flask-Login用户认证
login_manager.login_view = 'login'  # 设置登录页面视图
login_manager.login_message = '请先登录访问此页面'

# ==================== 加载CSV数据 ====================
# 主数据集文件路径
CSV_FILE = os.path.join(os.path.dirname(__file__), 'data', '零售行业_经营与贷款数据集_3000条.csv')
try:
    # 使用utf-8-sig编码读取CSV（支持BOM头）
    df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
    print(f"成功加载CSV数据，共 {len(df)} 条记录")
except Exception as e:
    print(f"加载CSV数据失败: {e}")
    df = pd.DataFrame()  # 如果加载失败，创建空DataFrame

# ==================== 数据库模型 ====================

class User(db.Model, UserMixin):
    """
    用户模型
    存储用户认证信息和个人资料
    """
    id = db.Column(db.Integer, primary_key=True)  # 用户ID（主键）
    username = db.Column(db.String(80), unique=True, nullable=False)  # 用户名（唯一）
    email = db.Column(db.String(120), unique=True, nullable=False)  # 邮箱（唯一）
    password_hash = db.Column(db.String(120), nullable=False)  # 密码哈希值
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 注册时间
    operation_logs = db.relationship('OperationLog', backref='user', lazy=True)  # 关联操作日志

    def set_password(self, password):
        """设置密码：使用werkzeug加密密码"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码：检查密码是否匹配哈希值"""
        return check_password_hash(self.password_hash, password)

    def is_authenticated(self):
        """用户是否已认证"""
        return True

    def is_anonymous(self):
        """用户是否为匿名用户"""
        return False


class OperationLog(db.Model):
    """
    操作日志模型
    记录用户的所有操作，用于审计和安全追踪
    """
    id = db.Column(db.Integer, primary_key=True)  # 日志ID（主键）
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 关联的用户ID
    action = db.Column(db.String(100), nullable=False)  # 操作类型（登录、访问、导出等）
    details = db.Column(db.Text)  # 操作详情
    ip_address = db.Column(db.String(50))  # 操作来源IP地址
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 操作时间


class UploadHistory(db.Model):
    """
    上传历史记录模型
    记录用户上传数据的历史信息
    """
    id = db.Column(db.Integer, primary_key=True)  # 记录ID（主键）
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 上传用户ID
    filename = db.Column(db.String(255), nullable=False)  # 文件名
    record_count = db.Column(db.Integer, nullable=False)  # 记录数量
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)  # 上传时间
    status = db.Column(db.String(50), default='success')  # 上传状态：success/error

# ==================== 创建数据库表 ====================
with app.app_context():
    try:
        db.create_all()  # 创建所有定义的数据库表
        print("数据库表创建成功")
    except Exception as e:
        print(f"数据库创建警告: {e}")

# ==================== 用户加载回调 ====================
@login_manager.user_loader
def load_user(user_id):
    """Flask-Login要求：根据用户ID加载用户对象"""
    return User.query.get(int(user_id))

# ==================== 辅助函数 ====================

def log_operation(user_id, action, details, ip_address=None):
    """
    记录用户操作日志
    
    Args:
        user_id: 用户ID
        action: 操作类型（如'用户登录'、'访问仪表板'等）
        details: 操作详情描述
        ip_address: 用户IP地址（可选，默认从request获取）
    """
    if not ip_address:
        ip_address = request.remote_addr if request else 'unknown'
    if not ip_address:
        ip_address = 'unknown'
    log = OperationLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_address
    )
    db.session.add(log)  # 添加日志到数据库会话
    db.session.commit()  # 提交事务


def get_risk_level(score):
    """
    根据信用评分确定风险等级
    
    Args:
        score: 企业信用评分（0-1000）
    
    Returns:
        tuple: (风险等级文本, Bootstrap颜色类名)
    """
    if score < 400:
        return '高风险', 'danger'
    elif score < 700:
        return '中风险', 'warning'
    else:
        return '低风险', 'success'

# ==================== 路由：认证相关 ====================

@app.route('/')
def index():
    """
    首页路由
    显示平台介绍和功能入口
    """
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    登录页面和处理
    GET: 显示登录表单
    POST: 处理登录请求
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)  # 是否记住登录状态

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)  # 登录用户
            try:
                log_operation(user.id, '用户登录', f'用户 {username} 登录成功')
            except Exception as e:
                print(f"日志记录失败: {e}")
            next_page = request.args.get('next')  # 跳转到登录前的页面
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('用户名或密码错误', 'danger')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    注册页面和处理
    GET: 显示注册表单
    POST: 处理注册请求
    """
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # 验证两次密码是否一致
        if password != confirm_password:
            flash('两次输入的密码不一致', 'warning')
            return redirect(url_for('register'))

        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'warning')
            return redirect(url_for('register'))

        # 检查邮箱是否已被注册
        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册', 'warning')
            return redirect(url_for('register'))

        # 创建新用户
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        try:
            log_operation(user.id, '用户注册', f'用户 {username} 注册成功')
        except Exception as e:
            print(f"日志记录失败: {e}")

        flash('注册成功！请登录', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required  # 需要登录才能访问
def logout():
    """登出路由：清除用户会话"""
    log_operation(current_user.id, '用户登出', f'用户 {current_user.username} 登出')
    logout_user()  # 清除用户会话
    flash('您已成功登出', 'info')
    return redirect(url_for('index'))

# ==================== 路由：主功能模块 ====================

@app.route('/dashboard')
@login_required
def dashboard():
    if df.empty:
        return render_template('dashboard.html', stats=None, charts_data=None)

    stats = {
        'total_companies': len(df),
        'loan_pass_rate': len(df[df['是否通过贷款'] == 1]) / len(df) * 100,
        'avg_credit_score': df['企业信用评分'].mean(),
        'avg_monthly_revenue': df['月均营收（万元）'].mean()
    }

    charts_data = {
        'city_distribution': df['城市等级'].value_counts().to_dict(),
        'retail_category': df['零售品类'].value_counts().to_dict(),
        'credit_distribution': df['企业信用评分'].value_counts().sort_index().to_dict()
    }

    log_operation(current_user.id, '访问仪表板', '用户访问仪表板页面')

    return render_template('dashboard.html', stats=stats, charts_data=charts_data)

@app.route('/risk_control')
@login_required
def risk_control():
    if df.empty:
        return render_template('risk_control.html', data=None, charts_data=None)

    # 风险等级统计
    high_risk = df[df['企业信用评分'] < 400]
    medium_risk = df[(df['企业信用评分'] >= 400) & (df['企业信用评分'] < 700)]
    low_risk = df[df['企业信用评分'] >= 700]

    risk_stats = {
        'high_risk': len(high_risk),
        'medium_risk': len(medium_risk),
        'low_risk': len(low_risk)
    }

    # 信用评分与贷款通过率关联分析
    score_ranges = [(0, 400), (400, 700), (700, 1000)]
    loan_pass_by_score = []
    for min_score, max_score in score_ranges:
        subset = df[(df['企业信用评分'] >= min_score) & (df['企业信用评分'] < max_score)]
        if len(subset) > 0:
            pass_rate = len(subset[subset['是否通过贷款'] == 1]) / len(subset) * 100
            loan_pass_by_score.append({
                'range': f'{min_score}-{max_score}',
                'pass_rate': pass_rate
            })

    # 风险建议
    risk_suggestions = []
    if len(high_risk) > 0:
        high_risk_pass = len(high_risk[high_risk['是否通过贷款'] == 1]) / len(high_risk) * 100
        risk_suggestions.append(f'高风险企业贷款通过率仅 {high_risk_pass:.1f}%，建议加强审核')

    if len(low_risk) > 0:
        low_risk_pass = len(low_risk[low_risk['是否通过贷款'] == 1]) / len(low_risk) * 100
        risk_suggestions.append(f'低风险企业贷款通过率达 {low_risk_pass:.1f}%，可优先处理')

    charts_data = {
        'risk_distribution': risk_stats,
        'loan_pass_by_score': loan_pass_by_score,
        'suggestions': risk_suggestions
    }

    # 获取风险数据列表
    risk_data = df.copy()
    risk_data['risk_level'] = risk_data['企业信用评分'].apply(
        lambda x: '高风险' if x < 400 else ('中风险' if x < 700 else '低风险')
    )

    log_operation(current_user.id, '访问智慧风控', '用户访问智慧风控页面')

    return render_template('risk_control.html', data=risk_data.head(20), charts_data=charts_data)

@app.route('/business_analysis')
@login_required
def business_analysis():
    """
    经营分析页面
    展示企业经营指标分析和零售品类对比
    """
    if df.empty:
        return render_template('business_analysis.html', data=None, charts_data=None)

    # 经营指标分析
    business_stats = {
        'avg_revenue': df['月均营收（万元）'].mean(),
        'avg_cost': df['月均成本（万元）'].mean(),
        'avg_profit': (df['月均营收（万元）'] - df['月均成本（万元）']).mean(),
        'avg_years': df['经营年份'].mean(),
        'avg_employees': df['员工人数'].mean()
    }

    # 零售品类对比分析
    category_analysis = df.groupby('零售品类').agg({
        '月均营收（万元）': 'mean',
        '月均成本（万元）': 'mean',
        '月均客流量（人）': 'mean'
    }).round(2).to_dict('index')

    # 生成经营建议
    suggestions = []
    top_revenue_category = df.groupby('零售品类')['月均营收（万元）'].mean().idxmax()
    suggestions.append(f'{top_revenue_category} 类企业营收表现最佳，可作为标杆分析')

    top_profit_category = (df['月均营收（万元）'] - df['月均成本（万元）']).groupby(df['零售品类']).mean().idxmax()
    suggestions.append(f'{top_profit_category} 类企业利润率最高，建议学习其经营模式')

    charts_data = {
        'business_stats': business_stats,
        'category_analysis': category_analysis,
        'suggestions': suggestions,
        'employee_distribution': df['员工人数'].value_counts().sort_index().to_dict()
    }

    log_operation(current_user.id, '访问经营分析', '用户访问经营分析页面')
    return render_template('business_analysis.html', data=df.head(20), charts_data=charts_data)

@app.route('/data_detail')
@login_required
def data_detail():
    """
    数据详情页面
    支持搜索、筛选和分页查看企业数据
    """
    if df.empty:
        return render_template('data_detail.html', data=None, page=1, total_pages=1, per_page=20)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # 限制每页显示数量范围
    if per_page not in [10, 20, 50, 100]:
        per_page = 20

    # 数据筛选
    filtered_df = df.copy()

    # 按企业名称或城市搜索
    search = request.args.get('search', '')
    if search:
        filtered_df = filtered_df[
            filtered_df['行业名称'].str.contains(search, na=False) |
            filtered_df['所在城市'].str.contains(search, na=False)
        ]

    # 按城市等级筛选
    city_level = request.args.get('city_level', '')
    if city_level:
        filtered_df = filtered_df[filtered_df['城市等级'] == city_level]

    # 按零售品类筛选
    retail_category = request.args.get('retail_category', '')
    if retail_category:
        filtered_df = filtered_df[filtered_df['零售品类'] == retail_category]

    # 分页处理
    total_records = len(filtered_df)
    total_pages = (total_records + per_page - 1) // per_page

    # 确保页码在有效范围内
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    data = filtered_df.iloc[start_idx:end_idx]

    # 获取筛选选项
    city_levels = df['城市等级'].unique().tolist()
    retail_categories = df['零售品类'].unique().tolist()

    log_operation(current_user.id, '访问数据详情', f'查看第 {page} 页数据，每页 {per_page} 条')

    return render_template('data_detail.html',
                         data=data,
                         page=page,
                         total_pages=total_pages,
                         search=search,
                         city_level=city_level,
                         retail_category=retail_category,
                         city_levels=city_levels,
                         retail_categories=retail_categories,
                         per_page=per_page,
                         total_records=total_records)

# ==================== 路由：数据导出 ====================

@app.route('/export_data')
@login_required
def export_data():
    """
    导出全部企业数据为CSV文件
    """
    if df.empty:
        flash('数据未加载', 'error')
        return redirect(url_for('data_detail'))

    # 创建CSV输出流
    output = io.StringIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)

    log_operation(current_user.id, '导出数据', '用户导出全部数据')

    # 生成响应并下载
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=retail_data_export.csv'
    response.headers['Content-type'] = 'text/csv'
    return response


@app.route('/export_user_data')
@login_required
def export_user_data():
    """
    导出当前用户的个人数据为CSV文件
    """
    user_data = {
        '用户名': [current_user.username],
        '邮箱': [current_user.email],
        '注册时间': [current_user.created_at.strftime('%Y-%m-%d %H:%M:%S')]
    }

    output = io.StringIO()
    pd.DataFrame(user_data).to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)

    log_operation(current_user.id, '导出个人数据', '用户导出个人数据')

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=user_data.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

# ==================== 路由：用户管理 ====================

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    个人资料页面
    GET: 显示用户个人资料
    POST: 更新用户信息
    """
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')

        # 检查邮箱是否已被其他用户使用
        if email != current_user.email and User.query.filter_by(email=email).first():
            flash('邮箱已被使用', 'warning')
            return redirect(url_for('profile'))

        # 检查用户名是否已被其他用户使用
        if username != current_user.username and User.query.filter_by(username=username).first():
            flash('用户名已被使用', 'warning')
            return redirect(url_for('profile'))

        # 更新用户信息
        current_user.email = email
        current_user.username = username
        db.session.commit()

        log_operation(current_user.id, '更新个人资料', f'用户更新个人资料')

        flash('个人资料更新成功', 'success')
        return redirect(url_for('profile'))

    log_operation(current_user.id, '访问个人资料', '用户访问个人资料页面')
    return render_template('profile.html')


@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """
    修改密码路由
    处理用户密码修改请求
    """
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    # 验证原密码
    if not current_user.check_password(old_password):
        flash('原密码错误', 'danger')
        return redirect(url_for('profile'))

    # 验证两次新密码是否一致
    if new_password != confirm_password:
        flash('两次输入的新密码不一致', 'warning')
        return redirect(url_for('profile'))

    # 更新密码
    current_user.set_password(new_password)
    db.session.commit()

    log_operation(current_user.id, '修改密码', '用户修改密码')

    flash('密码修改成功，请重新登录', 'success')
    return redirect(url_for('logout'))


@app.route('/operation_logs')
@login_required
def operation_logs():
    """
    操作日志页面
    显示当前用户的所有操作历史记录
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # 查询当前用户的操作日志，按时间倒序排列
    logs = OperationLog.query.filter_by(user_id=current_user.id)\
        .order_by(OperationLog.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    log_operation(current_user.id, '访问操作日志', f'用户查看操作日志第 {page} 页')
    return render_template('operation_logs.html', logs=logs, page=page, per_page=per_page)


@app.route('/settings')
@login_required
def settings():
    """
    系统设置页面
    显示系统配置和偏好设置
    """
    log_operation(current_user.id, '访问系统设置', '用户访问系统设置页面')
    return render_template('settings.html')

# ==================== 数据上传功能 ====================

@app.route('/upload_data', methods=['GET', 'POST'])
@login_required
def upload_data():
    """
    数据上传页面和处理
    GET: 显示上传页面和历史记录
    POST: 处理CSV文件上传和验证
    """
    if request.method == 'GET':
        log_operation(current_user.id, '访问数据上传', '用户访问数据上传页面')
        # 获取上传历史（最近10条）
        upload_history = UploadHistory.query.order_by(UploadHistory.upload_time.desc()).limit(10).all()
        return render_template('upload_data.html', upload_history=upload_history)

    if request.method == 'POST':
        try:
            # ==================== 文件验证 ====================
            # 检查是否有文件上传
            if 'file' not in request.files:
                flash('没有选择文件', 'danger')
                return redirect(url_for('upload_data'))

            file = request.files['file']

            # 检查文件名
            if file.filename == '':
                flash('没有选择文件', 'danger')
                return redirect(url_for('upload_data'))

            # 检查文件扩展名（仅支持CSV）
            if not file.filename.lower().endswith('.csv'):
                flash('仅支持 CSV 格式文件', 'danger')
                return redirect(url_for('upload_data'))

            # 检查文件大小（50MB限制）
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            max_size = 50 * 1024 * 1024  # 50MB

            if file_size > max_size:
                flash(f'文件大小超过 50MB 限制（当前大小：{file_size / (1024 * 1024):.2f} MB）', 'danger')
                return redirect(url_for('upload_data'))

            # ==================== 读取CSV文件 ====================
            try:
                # 尝试多种编码方式（支持UTF-8和GBK）
                encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']
                df_new = None
                used_encoding = None

                for encoding in encodings:
                    try:
                        file.seek(0)
                        df_new = pd.read_csv(file, encoding=encoding)
                        used_encoding = encoding
                        break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        continue

                if df_new is None:
                    flash('无法读取文件，请确保文件编码为 UTF-8 或 GBK', 'danger')
                    return redirect(url_for('upload_data'))

            except Exception as e:
                flash(f'读取CSV文件失败: {str(e)}', 'danger')
                return redirect(url_for('upload_data'))

            # ==================== CSV字段验证 ====================
            required_columns = [
                '企业ID', '行业名称', '经营年份', '注册金额（万元）', '所在城市', '城市等级',
                '企业信用评分', '月均营收（万元）', '月均成本（万元）', '员工人数',
                '是否通过贷款', '零售品类', '门店面积（㎡）', '月均客流量（人）'
            ]

            missing_columns = [col for col in required_columns if col not in df_new.columns]
            if missing_columns:
                flash(f'CSV文件缺少必要字段: {", ".join(missing_columns)}', 'danger')
                return redirect(url_for('upload_data'))

            # ==================== 数据验证 ====================
            try:
                # 验证企业ID唯一性
                if df_new['企业ID'].duplicated().any():
                    flash('企业ID存在重复，请检查数据', 'danger')
                    return redirect(url_for('upload_data'))

                # 验证数值字段
                numeric_columns = [
                    '经营年份', '注册金额（万元）', '企业信用评分',
                    '月均营收（万元）', '月均成本（万元）', '员工人数',
                    '门店面积（㎡）', '月均客流量（人）'
                ]
                for col in numeric_columns:
                    if col in df_new.columns:
                        df_new[col] = pd.to_numeric(df_new[col], errors='coerce')

                # 验证城市等级
                valid_city_levels = ['一线城市', '二线城市', '三线城市', '三线及以下']
                invalid_cities = df_new[~df_new['城市等级'].isin(valid_city_levels)]
                if not invalid_cities.empty:
                    flash(f'城市等级包含无效值，有效值为: {", ".join(valid_city_levels)}', 'danger')
                    return redirect(url_for('upload_data'))

                # 验证零售品类
                valid_categories = ['服饰零售', '生鲜零售', '家电零售', '综合商超', '文具零售']
                invalid_categories = df_new[~df_new['零售品类'].isin(valid_categories)]
                if not invalid_categories.empty:
                    flash(f'零售品类包含无效值，有效值为: {", ".join(valid_categories)}', 'danger')
                    return redirect(url_for('upload_data'))

                # 验证贷款状态
                valid_loan_status = ['通过', '拒绝', '1', '0', 1, 0]
                invalid_loans = df_new[~df_new['是否通过贷款'].astype(str).isin(['通过', '拒绝', '1', '0'])]
                if not invalid_loans.empty:
                    flash('是否通过贷款包含无效值，有效值为: 通过, 拒绝', 'danger')
                    return redirect(url_for('upload_data'))

                # 转换贷款状态为数值
                df_new['是否通过贷款'] = df_new['是否通过贷款'].map({
                    '通过': 1, '1': 1, 1: 1,
                    '拒绝': 0, '0': 0, 0: 0
                }).fillna(0)

            except Exception as e:
                flash(f'数据验证失败: {str(e)}', 'danger')
                return redirect(url_for('upload_data'))

            # ==================== 保存数据 ====================
            # 检查是否覆盖现有数据
            overwrite = request.form.get('overwrite') == 'on'

            if overwrite:
                # 备份原数据文件
                backup_filename = f"data/零售行业_经营与贷款数据集_3000条_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                try:
                    if os.path.exists(CSV_FILE):
                        import shutil
                        shutil.copy2(CSV_FILE, backup_filename)
                except Exception as e:
                    print(f"备份数据文件失败: {e}")

            # 保存新的CSV文件
            try:
                df_new.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')
            except Exception as e:
                flash(f'保存数据文件失败: {str(e)}', 'danger')
                return redirect(url_for('upload_data'))

            # 更新全局DataFrame
            global df
            df = df_new

            # ==================== 记录上传历史 ====================
            try:
                upload_record = UploadHistory(
                    user_id=current_user.id,
                    filename=file.filename,
                    record_count=len(df_new),
                    upload_time=datetime.utcnow(),
                    status='success'
                )
                db.session.add(upload_record)
                db.session.commit()
            except Exception as e:
                print(f"记录上传历史失败: {e}")

            # 记录操作日志
            log_operation(
                current_user.id,
                '上传数据',
                f'用户上传数据文件：{file.filename}，共 {len(df_new)} 条记录，覆盖：{overwrite}'
            )

            # 成功提示
            if overwrite:
                flash(f'数据上传成功！共 {len(df_new)} 条记录，已覆盖原有数据', 'success')
            else:
                flash(f'数据上传成功！共 {len(df_new)} 条记录', 'success')

            return redirect(url_for('dashboard'))

        except Exception as e:
            # 记录失败的上传历史
            try:
                upload_record = UploadHistory(
                    user_id=current_user.id,
                    filename=file.filename if 'file' in request.files else 'unknown',
                    record_count=0,
                    upload_time=datetime.utcnow(),
                    status='error'
                )
                db.session.add(upload_record)
                db.session.commit()
            except Exception as e2:
                print(f"记录上传历史失败: {e2}")

            flash(f'上传失败: {str(e)}', 'danger')
            return redirect(url_for('upload_data'))

# ==================== API 路由 ====================

@app.route('/api/stats')
@login_required
def api_stats():
    """
    获取统计数据API
    返回平台核心统计指标（JSON格式）
    """
    if df.empty:
        return jsonify({'error': '数据未加载'})

    stats = {
        'total_companies': len(df),
        'loan_pass_rate': len(df[df['是否通过贷款'] == 1]) / len(df) * 100,
        'avg_credit_score': df['企业信用评分'].mean(),
        'avg_monthly_revenue': df['月均营收（万元）'].mean()
    }
    return jsonify(stats)


# ==================== 详情数据API路由 ====================

@app.route('/api/detail/dashboard/<stat_type>')
@login_required
def dashboard_detail(stat_type):
    """
    获取仪表板统计卡片详情数据API
    
    Args:
        stat_type: 统计类型（total_companies, loan_pass_rate, avg_credit_score, avg_monthly_revenue）
    """
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    
    detail_files = {
        'total_companies': 'dashboard_total_companies_detail.csv',
        'loan_pass_rate': 'dashboard_loan_pass_detail.csv',
        'avg_credit_score': 'dashboard_credit_score_detail.csv',
        'avg_monthly_revenue': 'dashboard_monthly_revenue_detail.csv'
    }
    
    if stat_type not in detail_files:
        return jsonify({'error': '无效的统计类型'})
    
    try:
        detail_df = pd.read_csv(os.path.join(data_dir, detail_files[stat_type]), encoding='utf-8-sig')
        return jsonify({
            'success': True,
            'data': detail_df.to_dict('records'),
            'columns': detail_df.columns.tolist()
        })
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/detail/risk/<risk_level>')
@login_required
def risk_detail(risk_level):
    """
    获取智慧风控风险等级详情数据API
    
    Args:
        risk_level: 风险等级（high, medium, low）
    """
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    
    detail_files = {
        'high': 'risk_high_risk_detail.csv',
        'medium': 'risk_medium_risk_detail.csv',
        'low': 'risk_low_risk_detail.csv'
    }
    
    if risk_level not in detail_files:
        return jsonify({'error': '无效的风险等级'})
    
    try:
        detail_df = pd.read_csv(os.path.join(data_dir, detail_files[risk_level]), encoding='utf-8-sig')
        return jsonify({
            'success': True,
            'data': detail_df.head(50).to_dict('records'),  # 限制返回前50条
            'total_count': len(detail_df),
            'columns': detail_df.columns.tolist()
        })
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/detail/business/<business_type>')
@login_required
def business_detail(business_type):
    """
    获取经营分析详情数据API
    
    Args:
        business_type: 经营类型（revenue, cost, profit, years）
    """
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    
    detail_files = {
        'revenue': 'business_revenue_detail.csv',
        'cost': 'business_cost_detail.csv',
        'profit': 'business_profit_detail.csv',
        'years': 'business_years_detail.csv'
    }
    
    if business_type not in detail_files:
        return jsonify({'error': '无效的经营类型'})
    
    try:
        detail_df = pd.read_csv(os.path.join(data_dir, detail_files[business_type]), encoding='utf-8-sig')
        return jsonify({
            'success': True,
            'data': detail_df.to_dict('records'),
            'columns': detail_df.columns.tolist()
        })
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/detail/company/<company_id>')
@login_required
def company_detail_api(company_id):
    """
    获取企业详情数据API
    
    Args:
        company_id: 企业ID
    """
    try:
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        detail_df = pd.read_csv(os.path.join(data_dir, 'data_management_companies_detail.csv'), encoding='utf-8-sig')
        company = detail_df[detail_df['企业ID'] == company_id]

        if company.empty:
            return jsonify({'error': '企业不存在'})

        return jsonify({
            'success': True,
            'data': company.iloc[0].to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# ==================== 详情页面路由 ====================

@app.route('/dashboard_detail/<stat_type>')
@login_required
def dashboard_detail_page(stat_type):
    """仪表板统计详情页面"""
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # 限制每页显示数量范围
    if per_page not in [10, 20, 50, 100]:
        per_page = 20

    # 统计类型配置
    stat_configs = {
        'total_companies': {
            'title': '企业总数详情',
            'file': 'dashboard_total_companies_detail.csv',
            'color': 'primary',
            'summary_unit': '家',
            'description': '展示了不同城市等级的企业数量分布情况',
            'suggestions': [
                '一线城市企业数量占比约15%，市场竞争激烈',
                '二线城市企业数量最多，发展潜力大',
                '三线及以下城市企业数量占比超过40%，下沉市场广阔'
            ]
        },
        'loan_pass_rate': {
            'title': '贷款通过率详情',
            'file': 'dashboard_loan_pass_detail.csv',
            'color': 'success',
            'summary_unit': '%',
            'description': '展示了不同城市等级和零售品类的贷款通过率',
            'suggestions': [
                '一线城市企业贷款通过率相对较高',
                '生鲜零售和综合商超类企业通过率较高',
                '建议对低通过率行业加强风险审核'
            ]
        },
        'avg_credit_score': {
            'title': '平均信用评分详情',
            'file': 'dashboard_credit_score_detail.csv',
            'color': 'info',
            'summary_unit': '分',
            'description': '展示了不同零售品类和城市等级的平均信用评分',
            'suggestions': [
                '文具零售和综合商超类企业信用评分较高',
                '服饰零售类企业信用评分相对较低',
                '建议关注低信用评分行业的企业风险'
            ]
        },
        'avg_monthly_revenue': {
            'title': '月均营收详情',
            'file': 'dashboard_monthly_revenue_detail.csv',
            'color': 'warning',
            'summary_unit': '万元',
            'description': '展示了不同城市等级和零售品类的平均月营收',
            'suggestions': [
                '一线城市企业月均营收普遍较高',
                '综合商超和家电零售类企业营收较高',
                '生鲜零售类企业营收波动较大'
            ]
        }
    }

    if stat_type not in stat_configs:
        flash('无效的统计类型', 'danger')
        return redirect(url_for('dashboard'))

    config = stat_configs[stat_type]

    try:
        # 读取详情数据
        detail_df = pd.read_csv(os.path.join(data_dir, config['file']), encoding='utf-8-sig')

        # 分页处理
        total_count = len(detail_df)
        total_pages = (total_count + per_page - 1) // per_page

        # 确保页码在有效范围内
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_data = detail_df.iloc[start_idx:end_idx]

        # 计算汇总值
        if stat_type == 'total_companies':
            summary_value = len(df)
        elif stat_type == 'loan_pass_rate':
            summary_value = round(len(df[df['是否通过贷款'] == 1]) / len(df) * 100, 2)
        elif stat_type == 'avg_credit_score':
            summary_value = round(df['企业信用评分'].mean(), 2)
        else:
            summary_value = round(df['月均营收（万元）'].mean(), 2)

        return render_template('dashboard_detail.html',
                            title=config['title'],
                            color=config['color'],
                            summary_value=summary_value,
                            summary_unit=config['summary_unit'],
                            description=config['description'],
                            suggestions=config['suggestions'],
                            data=paginated_data.to_dict('records'),
                            columns=detail_df.columns.tolist(),
                            total_count=total_count,
                            page=page,
                            total_pages=total_pages,
                            per_page=per_page,
                            stat_type=stat_type,
                            analysis=None)
    except Exception as e:
        flash(f'加载数据失败: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/risk_detail/<risk_level>')
@login_required
def risk_detail_page(risk_level):
    """智慧风控详情页面"""
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # 限制每页显示数量范围
    if per_page not in [10, 20, 50, 100]:
        per_page = 20

    # 风险等级中英文映射
    risk_level_mapping = {
        '高风险': 'high',
        '中风险': 'medium',
        '低风险': 'low',
        'high': 'high',
        'medium': 'medium',
        'low': 'low'
    }

    # 映射风险等级
    mapped_risk_level = risk_level_mapping.get(risk_level)
    if not mapped_risk_level:
        flash('无效的风险等级', 'danger')
        return redirect(url_for('risk_control'))

    # 风险等级配置
    risk_configs = {
        'high': {
            'title': '高风险',
            'file': 'risk_high_risk_detail.csv',
            'color': 'danger',
            'score_range': '信用评分 < 400',
            'description': '信用评分低于400分，贷款违约风险极高',
            'suggestions': [
                '加强企业资质审核，严格把关',
                '要求提供更多担保措施',
                '降低贷款额度或提高利率',
                '密切关注企业经营状况'
            ]
        },
        'medium': {
            'title': '中风险',
            'file': 'risk_medium_risk_detail.csv',
            'color': 'warning',
            'score_range': '信用评分 400-699',
            'description': '信用评分在400-699分之间，存在一定违约风险',
            'suggestions': [
                '仔细评估企业经营状况',
                '适当控制贷款额度',
                '增加贷后监管频率',
                '建立风险预警机制'
            ]
        },
        'low': {
            'title': '低风险',
            'file': 'risk_low_risk_detail.csv',
            'color': 'success',
            'score_range': '信用评分 >= 700',
            'description': '信用评分700分以上，违约风险较低，还款能力较强',
            'suggestions': [
                '可以优先考虑贷款申请',
                '适当提高贷款额度',
                '提供更优惠的利率政策',
                '建立长期合作关系'
            ]
        }
    }

    if mapped_risk_level not in risk_configs:
        flash('无效的风险等级', 'danger')
        return redirect(url_for('risk_control'))

    config = risk_configs[mapped_risk_level]

    try:
        # 读取风险详情数据
        detail_df = pd.read_csv(os.path.join(data_dir, config['file']), encoding='utf-8-sig')

        # 分页处理
        total_count = len(detail_df)
        total_pages = (total_count + per_page - 1) // per_page

        # 确保页码在有效范围内
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_data = detail_df.iloc[start_idx:end_idx]

        # 计算统计信息
        high_risk = len(df[df['企业信用评分'] < 400])
        medium_risk = len(df[(df['企业信用评分'] >= 400) & (df['企业信用评分'] < 700)])
        low_risk = len(df[df['企业信用评分'] >= 700])

        # 计算贷款通过率
        if mapped_risk_level == 'high':
            pass_loans = len(df[(df['企业信用评分'] < 400) & (df['是否通过贷款'] == 1)])
            loan_pass_rate = round(pass_loans / high_risk * 100, 2) if high_risk > 0 else 0
        elif mapped_risk_level == 'medium':
            pass_loans = len(df[(df['企业信用评分'] >= 400) & (df['企业信用评分'] < 700) & (df['是否通过贷款'] == 1)])
            loan_pass_rate = round(pass_loans / medium_risk * 100, 2) if medium_risk > 0 else 0
        else:
            pass_loans = len(df[(df['企业信用评分'] >= 700) & (df['是否通过贷款'] == 1)])
            loan_pass_rate = round(pass_loans / low_risk * 100, 2) if low_risk > 0 else 0

        return render_template('risk_detail_page.html',
                            risk_level=config['title'],
                            color=config['color'],
                            risk_description=config['description'],
                            suggestions=config['suggestions'],
                            total_count=total_count,
                            loan_pass_rate=loan_pass_rate,
                            showing_count=len(paginated_data),
                            data=paginated_data.to_dict('records'),
                            columns=detail_df.columns.tolist(),
                            page=page,
                            total_pages=total_pages,
                            per_page=per_page)
    except Exception as e:
        flash(f'加载数据失败: {str(e)}', 'danger')
        return redirect(url_for('risk_control'))

@app.route('/business_detail/<business_type>')
@login_required
def business_detail_page(business_type):
    """经营分析详情页面"""
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # 限制每页显示数量范围
    if per_page not in [10, 20, 50, 100]:
        per_page = 20

    # 经营类型中英文映射
    business_type_mapping = {
        'avg_revenue': 'revenue',
        'avg_cost': 'cost',
        'avg_profit': 'profit',
        'avg_years': 'years',
        'revenue': 'revenue',
        'cost': 'cost',
        'profit': 'profit',
        'years': 'years'
    }

    # 映射经营类型
    mapped_business_type = business_type_mapping.get(business_type)
    if not mapped_business_type:
        flash('无效的经营类型', 'danger')
        return redirect(url_for('business_analysis'))

    # 经营类型配置
    business_configs = {
        'revenue': {
            'title': '月均营收',
            'file': 'business_revenue_detail.csv',
            'color': 'primary',
            'unit': '万元',
            'description': '展示了不同零售品类的月均营收分布情况',
            'suggestions': [
                '综合商超和家电零售类企业营收较高',
                '一线城市企业营收优势明显',
                '生鲜零售类企业受季节影响较大',
                '建议企业多元化经营以降低风险'
            ]
        },
        'cost': {
            'title': '月均成本',
            'file': 'business_cost_detail.csv',
            'color': 'danger',
            'unit': '万元',
            'description': '展示了不同零售品类的月均成本分布情况',
            'suggestions': [
                '房租和人工成本占比较高',
                '一线城市企业成本压力大',
                '建议优化运营流程降低成本',
                '考虑信息化管理提高效率'
            ]
        },
        'profit': {
            'title': '月均利润',
            'file': 'business_profit_detail.csv',
            'color': 'success',
            'unit': '万元',
            'description': '展示了不同零售品类的月均利润分布情况',
            'suggestions': [
                '文具零售和综合商超利润率较高',
                '利润率与企业经营年限正相关',
                '建议延长经营周期提高稳定性',
                '关注高利润品类的发展机会'
            ]
        },
        'years': {
            'title': '平均经营年限',
            'file': 'business_years_detail.csv',
            'color': 'info',
            'unit': '年',
            'description': '展示了不同城市等级和零售品类的平均经营年限',
            'suggestions': [
                '企业经营年限平均约5年',
                '经营年限越长稳定性越高',
                '生鲜零售类企业年限相对较短',
                '建议关注企业持续经营能力'
            ]
        }
    }

    if mapped_business_type not in business_configs:
        flash('无效的经营类型', 'danger')
        return redirect(url_for('business_analysis'))

    config = business_configs[mapped_business_type]

    try:
        # 读取经营详情数据
        detail_df = pd.read_csv(os.path.join(data_dir, config['file']), encoding='utf-8-sig')

        # 分页处理
        total_count = len(detail_df)
        total_pages = (total_count + per_page - 1) // per_page

        # 确保页码在有效范围内
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_data = detail_df.iloc[start_idx:end_idx]

        # 计算汇总值
        if mapped_business_type == 'revenue':
            summary_value = round(df['月均营收（万元）'].mean(), 2)
        elif mapped_business_type == 'cost':
            summary_value = round(df['月均成本（万元）'].mean(), 2)
        elif mapped_business_type == 'profit':
            summary_value = round((df['月均营收（万元）'] - df['月均成本（万元）']).mean(), 2)
        elif mapped_business_type == 'years':
            summary_value = round(df['经营年份'].mean(), 2)
        else:
            summary_value = 0

        # 准备图表数据（使用全部数据）
        chart_labels = detail_df['零售品类'].tolist() if '零售品类' in detail_df.columns else []
        chart_data = []

        if mapped_business_type == 'revenue':
            chart_data = detail_df['平均月营收(万元)'].tolist() if '平均月营收(万元)' in detail_df.columns else []
        elif mapped_business_type == 'cost':
            chart_data = detail_df['平均月成本(万元)'].tolist() if '平均月成本(万元)' in detail_df.columns else []
        elif mapped_business_type == 'profit':
            chart_data = detail_df['平均利润(万元)'].tolist() if '平均利润(万元)' in detail_df.columns else []
        else:
            chart_data = detail_df['平均经营年限(年)'].tolist() if '平均经营年限(年)' in detail_df.columns else []

        return render_template('business_detail_page.html',
                            business_name=config['title'],
                            color=config['color'],
                            summary_value=summary_value,
                            summary_unit=config['unit'],
                            description=config['description'],
                            suggestions=config['suggestions'],
                            data=paginated_data.to_dict('records'),
                            columns=detail_df.columns.tolist(),
                            total_count=total_count,
                            page=page,
                            total_pages=total_pages,
                            per_page=per_page,
                            business_type=business_type,
                            chart_labels=chart_labels,
                            chart_data=chart_data,
                            chart_label=f'{config["title"]}({config["unit"]})')
    except Exception as e:
        flash(f'加载数据失败: {str(e)}', 'danger')
        return redirect(url_for('business_analysis'))

@app.route('/company_detail/<company_id>')
@login_required
def company_detail_page(company_id):
    """企业详情页面"""
    try:
        # 从主数据文件读取企业信息
        if df.empty:
            flash('数据未加载', 'danger')
            return redirect(url_for('data_detail'))

        # 查找企业
        company = df[df['企业ID'] == company_id]

        if company.empty:
            flash('企业不存在', 'danger')
            return redirect(url_for('data_detail'))

        company_data = company.iloc[0].to_dict()

        # 计算利润和利润率
        revenue = company_data['月均营收（万元）']
        cost = company_data['月均成本（万元）']
        profit = revenue - cost
        profit_rate = (profit / revenue * 100) if revenue > 0 else 0
        avg_revenue_per_employee = (revenue / company_data['员工人数']) if company_data['员工人数'] > 0 else 0

        # 将计算出的值添加到company_data中
        company_data['利润(万元)'] = profit
        company_data['利润率(%)'] = profit_rate
        company_data['人均月营收(万元)'] = avg_revenue_per_employee

        # 计算风险等级
        credit_score = company_data['企业信用评分']
        if credit_score < 400:
            risk_level = '高风险'
            risk_color = 'danger'
        elif credit_score < 700:
            risk_level = '中风险'
            risk_color = 'warning'
        else:
            risk_level = '低风险'
            risk_color = 'success'

        # 记录操作日志
        try:
            log_operation(current_user.id, '查看企业详情', f'查看企业 {company_id} 详情')
        except Exception as log_error:
            print(f"日志记录失败: {log_error}")

        return render_template('company_detail.html',
                            company=company_data,
                            risk_level=risk_level,
                            risk_color=risk_color)
    except Exception as e:
        flash(f'加载数据失败: {str(e)}', 'danger')
        return redirect(url_for('data_detail'))

@app.route('/api/risk_distribution')
@login_required
def api_risk_distribution():
    if df.empty:
        return jsonify({'error': '数据未加载'})

    high_risk = len(df[df['企业信用评分'] < 400])
    medium_risk = len(df[(df['企业信用评分'] >= 400) & (df['企业信用评分'] < 700)])
    low_risk = len(df[df['企业信用评分'] >= 700])

    return jsonify({
        'high_risk': high_risk,
        'medium_risk': medium_risk,
        'low_risk': low_risk
    })

def predict_loan_pass_rate(credit_score, revenue, cost):
    """
    预测企业贷款通过率
    基于多因素加权评分模型
    
    Args:
        credit_score: 企业信用评分（0-1000）
        revenue: 月均营收（万元）
        cost: 月均成本（万元）
    
    Returns:
        float: 预测的贷款通过概率（0-100）
    
    算法说明:
        - 信用评分权重：60%（决定基础概率）
        - 利润率权重：30%（调整因子）
        - 综合计算预测概率
    """
    # 根据信用评分确定基础概率
    if credit_score < 400:
        base_probability = 0.3  # 高信用风险，基础通过率30%
    elif credit_score < 600:
        base_probability = 0.6  # 中等信用风险，基础通过率60%
    elif credit_score < 700:
        base_probability = 0.8  # 较低信用风险，基础通过率80%
    else:
        base_probability = 0.95  # 低信用风险，基础通过率95%

    # 计算利润率
    profit = revenue - cost
    profit_rate = (profit / revenue * 100) if revenue > 0 else 0

    # 利润率调整因子
    if profit_rate > 30:
        profit_factor = 1.2  # 高利润率，通过率提升20%
    elif profit_rate > 20:
        profit_factor = 1.1  # 较高利润率，通过率提升10%
    elif profit_rate > 10:
        profit_factor = 1.0  # 正常利润率，不调整
    elif profit_rate > 0:
        profit_factor = 0.9  # 低利润率，通过率降低10%
    else:
        profit_factor = 0.7  # 亏损，通过率降低30%

    # 综合预测概率 = 基础概率 × 利润率调整因子
    predicted_probability = base_probability * profit_factor

    # 确保概率在0-100之间
    predicted_probability = max(0, min(1, predicted_probability))

    return round(predicted_probability * 100, 2)


def predict_revenue_trend(category, years):
    """
    预测企业营收增长趋势
    基于品类和经营年限的趋势模型
    
    Args:
        category: 零售品类
        years: 经营年限
    
    Returns:
        dict: 包含增长率、稳定性、趋势方向
    """
    # 各品类的基础增长率和稳定性配置
    category_trend = {
        '综合商超': {'growth_rate': 0.05, 'stability': 0.9},  # 稳定增长
        '生鲜零售': {'growth_rate': 0.08, 'stability': 0.7},  # 增长较快但波动大
        '服饰零售': {'growth_rate': 0.06, 'stability': 0.75},  # 中等增长
        '家电零售': {'growth_rate': 0.04, 'stability': 0.85},  # 稳定但增长较慢
        '文具零售': {'growth_rate': 0.03, 'stability': 0.95}   # 非常稳定
    }

    trend = category_trend.get(category, {'growth_rate': 0.05, 'stability': 0.8})

    # 经营年限影响因子
    if years < 2:
        years_factor = 0.8  # 新企业，增长率较低
    elif years < 5:
        years_factor = 1.0  # 成长期企业，正常增长
    elif years < 10:
        years_factor = 1.1  # 成熟企业，增长稍快
    else:
        years_factor = 1.05  # 老牌企业，增长趋于稳定

    # 预测增长率 = 品类基础增长率 × 年限因子
    predicted_growth = trend['growth_rate'] * years_factor

    return {
        'growth_rate': round(predicted_growth * 100, 2),
        'stability': trend['stability'],
        'trend': '上升' if predicted_growth > 0 else '下降'
    }


def predict_risk_level(credit_score, years, profit_rate):
    """
    预测企业未来风险等级
    基于信用评分、经营年限和利润率的综合评估
    
    Args:
        credit_score: 企业信用评分
        years: 经营年限
        profit_rate: 利润率（%）
    
    Returns:
        tuple: (风险等级文本, 风险评分, Bootstrap颜色类名)
    
    算法说明:
        - 基础风险分（0-100）主要由信用评分决定
        - 经营年限调整：年限越短，风险越高
        - 利润率调整：利润率越高，风险越低
    """
    # 基础风险分（信用评分）
    if credit_score < 400:
        risk_score = 80  # 高信用风险，基础风险分80
    elif credit_score < 600:
        risk_score = 50  # 中等信用风险，基础风险分50
    elif credit_score < 700:
        risk_score = 30  # 较低信用风险，基础风险分30
    else:
        risk_score = 15  # 低信用风险，基础风险分15

    # 经营年限调整
    if years < 1:
        risk_score += 15  # 新企业，风险+15
    elif years < 3:
        risk_score += 5   # 年限较短，风险+5
    elif years < 5:
        risk_score -= 5   # 年限适中，风险-5
    else:
        risk_score -= 10  # 老企业，风险-10

    # 利润率调整
    if profit_rate < 0:
        risk_score += 20  # 亏损，风险+20
    elif profit_rate < 10:
        risk_score += 5   # 低利润，风险+5
    elif profit_rate > 30:
        risk_score -= 10  # 高利润，风险-10

    # 确保风险分在0-100之间
    risk_score = max(0, min(100, risk_score))

    # 确定风险等级
    if risk_score >= 70:
        return '高风险', risk_score, 'danger'
    elif risk_score >= 40:
        return '中风险', risk_score, 'warning'
    else:
        return '低风险', risk_score, 'success'

@app.route('/prediction')
@login_required
def prediction():
    """
    数据预测页面
    提供基于多因素模型的企业贷款通过率、风险等级、营收趋势预测
    """
    if df.empty:
        flash('数据未加载，无法进行预测', 'danger')
        return redirect(url_for('dashboard'))

    # 获取预测参数
    credit_score = request.args.get('credit_score', type=int)
    revenue = request.args.get('revenue', type=float)
    cost = request.args.get('cost', type=float)
    category = request.args.get('category', '')
    years = request.args.get('years', type=float)

    # 获取零售品类列表
    categories = df['零售品类'].unique().tolist()

    # 如果没有提供参数，使用默认值
    prediction_result = None
    if credit_score and revenue is not None and cost is not None:
        # 预测贷款通过率
        loan_pass_prob = predict_loan_pass_rate(credit_score, revenue, cost)

        # 预测风险等级
        profit_rate = ((revenue - cost) / revenue * 100) if revenue > 0 else 0
        risk_level, risk_score, risk_color = predict_risk_level(credit_score, years if years else 5, profit_rate)

        # 预测营收趋势
        if category:
            revenue_trend = predict_revenue_trend(category, years if years else 5)
        else:
            revenue_trend = None

        prediction_result = {
            'loan_pass_prob': loan_pass_prob,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_color': risk_color,
            'revenue_trend': revenue_trend,
            'profit_rate': round(profit_rate, 2)
        }

    # 生成整体市场预测
    market_predictions = generate_market_predictions()

    return render_template('prediction.html',
                         categories=categories,
                         prediction_result=prediction_result,
                         market_predictions=market_predictions,
                         current_params={
                             'credit_score': credit_score,
                             'revenue': revenue,
                             'cost': cost,
                             'category': category,
                             'years': years
                         })


def generate_market_predictions():
    """
    生成整体市场预测数据
    对每个零售品类进行综合预测分析
    """
    if df.empty:
        return None

    # 各品类的平均数据
    category_stats = df.groupby('零售品类').agg({
        '月均营收（万元）': 'mean',
        '月均成本（万元）': 'mean',
        '企业信用评分': 'mean',
        '经营年份': 'mean'
    }).to_dict('index')

    market_predictions = []
    for category, stats in category_stats.items():
        avg_revenue = stats['月均营收（万元）']
        avg_cost = stats['月均成本（万元）']
        avg_credit = stats['企业信用评分']
        avg_years = stats['经营年份']

        # 预测该品类的整体趋势
        trend = predict_revenue_trend(category, avg_years)

        # 预测整体贷款通过率
        pass_rate = predict_loan_pass_rate(avg_credit, avg_revenue, avg_cost)

        # 预测风险分布
        profit_rate = ((avg_revenue - avg_cost) / avg_revenue * 100) if avg_revenue > 0 else 0
        risk_level, risk_score, risk_color = predict_risk_level(avg_credit, avg_years, profit_rate)

        market_predictions.append({
            'category': category,
            'avg_revenue': round(avg_revenue, 2),
            'predicted_growth': trend['growth_rate'],
            'trend': trend['trend'],
            'stability': trend['stability'],
            'pass_rate': pass_rate,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_color': risk_color
        })

    return market_predictions


@app.route('/api/predict', methods=['POST'])
@login_required
def api_predict():
    """
    预测API接口
    接收POST请求，返回企业预测结果
    
    请求体格式:
        {
            "credit_score": int,
            "revenue": float,
            "cost": float,
            "category": string (可选),
            "years": int (可选)
        }
    """
    data = request.get_json()

    credit_score = data.get('credit_score')
    revenue = data.get('revenue')
    cost = data.get('cost')
    category = data.get('category')
    years = data.get('years')

    # 验证必要参数
    if not all([credit_score, revenue is not None, cost is not None]):
        return jsonify({'error': '缺少必要参数'}), 400

    # 执行预测
    loan_pass_prob = predict_loan_pass_rate(credit_score, revenue, cost)
    profit_rate = ((revenue - cost) / revenue * 100) if revenue > 0 else 0
    risk_level, risk_score, risk_color = predict_risk_level(credit_score, years if years else 5, profit_rate)

    result = {
        'loan_pass_probability': loan_pass_prob,
        'risk_level': risk_level,
        'risk_score': risk_score,
        'profit_rate': round(profit_rate, 2)
    }

    # 如果提供了品类，增加营收趋势预测
    if category:
        revenue_trend = predict_revenue_trend(category, years if years else 5)
        result['revenue_trend'] = revenue_trend

    return jsonify(result)

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found_error(error):
    """
    404错误处理
    当用户访问不存在的页面时触发
    """
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """
    500错误处理
    当服务器内部发生错误时触发
    注意：遇到数据库错误时会回滚事务
    """
    db.session.rollback()  # 回滚数据库事务，防止数据不一致
    return render_template('500.html'), 500


# ==================== 主程序入口 ====================

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='零售行业经营与贷款智慧风控平台')
    parser.add_argument('--port', type=int, default=5000, help='指定端口号（默认：5000）')
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("零售行业经营与贷款智慧风控平台")
    print(f"{'='*60}")
    print(f"访问地址: http://localhost:{args.port}")
    print(f"{'='*60}\n")

    # 启动Flask应用
    # host='0.0.0.0': 允许外部访问
    # port=args.port: 使用命令行指定的端口
    # debug=True: 开启调试模式，代码修改后自动重载
    app.run(host='0.0.0.0', port=args.port, debug=True)
