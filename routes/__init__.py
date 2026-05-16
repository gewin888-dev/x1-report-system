# routes/__init__.py
"""X1 路由模块 - Blueprint 注册入口"""


def register_blueprints(app):
    """注册所有 Blueprint 到 Flask app"""
    from routes.settings import settings_bp
    from routes.projects import projects_bp
    from routes.tasks import tasks_bp
    from routes.records import records_bp
    from routes.drafts import drafts_bp
    from routes.export import export_bp
    from routes.template_mgmt import template_mgmt_bp
    from routes.admin_misc import admin_misc_bp

    app.register_blueprint(settings_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(drafts_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(template_mgmt_bp)
    app.register_blueprint(admin_misc_bp)
