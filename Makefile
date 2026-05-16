.PHONY: test test-full lint build build-min watch start stop restart status doctor

# 测试
test:
	cd /Users/fuwuqi/检测报告生成系统_X1 && python3 -m pytest tests/ -x -q

test-full:
	cd /Users/fuwuqi/检测报告生成系统_X1 && python3 -m pytest tests/ --tb=short -v

# 代码检查
lint:
	python3 -m py_compile app_x1.py
	@for f in routes/*.py helpers/*.py; do python3 -m py_compile $$f && echo "  ✓ $$f"; done

# 前端构建
build:
	esbuild static/src/record/index.js --bundle --outfile=static/dist/record.bundle.js --format=iife --target=es2018

build-min:
	esbuild static/src/record/index.js --bundle --outfile=static/dist/record.bundle.min.js --format=iife --target=es2018 --minify

watch:
	esbuild static/src/record/index.js --bundle --outfile=static/dist/record.bundle.js --format=iife --target=es2018 --watch

# 服务管理
start:
	bash scripts/start_x1_daemon.sh

stop:
	bash scripts/stop_x1_daemon.sh

restart:
	bash scripts/restart_x1_daemon.sh

status:
	bash scripts/status_x1_daemon.sh

doctor:
	bash scripts/doctor_x1_daemon.sh
