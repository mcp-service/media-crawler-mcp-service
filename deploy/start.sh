#!/bin/bash
###############################################################################
# MCP Tools Service - 启动脚本
#
# 使用方法:
#   cd deploy && ./start.sh [dev|prod]
#
# 选项:
#   dev   - 开发模式（Poetry + 本地）
#   prod  - 生产模式（Docker Compose）
###############################################################################

set -e

MODE="${1:-dev}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "  Media Crawler MCP - 社交媒体爬虫 MCP 服务"
echo "  模式: $MODE"
echo "========================================"

if [ "$MODE" = "dev" ]; then
    echo "启动开发模式..."
    cd "$PROJECT_ROOT"

    # 检查 .env 文件
    if [ ! -f .env ]; then
        echo "警告: .env 文件不存在"
        if [ -f .env.example ]; then
            cp .env.example .env
            echo "✓ 已从 .env.example 创建 .env 文件"
        else
            echo "错误: .env.example 文件不存在"
            exit 1
        fi
    fi

    # 检查 Poetry
    if ! command -v poetry &> /dev/null; then
        echo "错误: Poetry 未安装"
        echo "请安装 Poetry: curl -sSL https://install.python-poetry.org | python3 -"
        exit 1
    fi

    # 安装依赖（如果需要）
    if ! poetry env info &> /dev/null; then
        echo "正在安装依赖..."
        poetry install
    fi

    # 启动服务
    echo ""
    echo "✓ 正在启动 MCP 服务..."
    echo "  - MCP SSE: http://localhost:9090/sse"
    echo "  - 管理服务: http://localhost:9091"
    echo ""
    poetry run python main.py --transport both

elif [ "$MODE" = "prod" ]; then
    echo "启动生产模式（Docker Compose）..."
    cd "$SCRIPT_DIR"

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        echo "错误: Docker 未安装"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        echo "错误: Docker 服务未运行"
        echo "请先启动 Docker"
        exit 1
    fi

    # 检查 .env 文件
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        echo "警告: .env 文件不存在"
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
            echo "✓ 已从 .env.example 创建 .env 文件"
        fi
    fi

    # 获取 Docker Compose 命令
    if docker compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        echo "错误: Docker Compose 未安装"
        exit 1
    fi

    # 启动服务
    echo ""
    echo "正在启动 Docker 服务..."
    $COMPOSE_CMD up -d

    # 等待服务启动
    echo "等待服务启动..."
    sleep 5

    # 检查服务状态
    echo ""
    echo "服务状态:"
    $COMPOSE_CMD ps

    echo ""
    echo "========================================"
    echo "✓ 服务启动成功！"
    echo "========================================"
    echo ""
    echo "服务地址:"
    echo "  - MCP SSE:  http://localhost:9090/sse"
    echo "  - 管理服务: http://localhost:9091"
    echo "  - 健康检查: http://localhost:9090/health"
    echo ""
    echo "常用命令:"
    echo "  查看日志: cd deploy && $COMPOSE_CMD logs -f"
    echo "  停止服务: cd deploy && $COMPOSE_CMD down"
    echo "  重启服务: cd deploy && $COMPOSE_CMD restart"
    echo ""

else
    echo "错误: 未知模式 '$MODE'"
    echo "使用方法: $0 [dev|prod]"
    echo ""
    echo "选项:"
    echo "  dev   - 开发模式（本地运行）"
    echo "  prod  - 生产模式（Docker）"
    exit 1
fi
