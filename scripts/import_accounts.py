#!/usr/bin/env python
"""
导入公众号清单脚本
"""
import sys
import csv
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.database import SessionLocal, OfficialAccount
from shared.utils import get_logger

logger = get_logger("import_accounts")


def import_accounts(csv_file: str):
    """
    从CSV文件导入公众号
    
    CSV格式：
    werss_feed_id,name,is_active,wechat_id
    """
    db = SessionLocal()
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            
            for row in reader:
                # 检查是否已存在
                existing = db.query(OfficialAccount).filter(
                    OfficialAccount.wechat_id == row['wechat_id']
                ).first()
                
                if existing:
                    logger.info(f"Account {row['name']} already exists, skipping")
                    continue
                
                # 处理 is_active 字段
                is_active_raw = row.get('is_active', '1').strip()
                is_active = (is_active_raw == '1' or is_active_raw.lower() == 'true')
                
                # 创建新公众号
                account = OfficialAccount(
                    name=row['name'],
                    wechat_id=row['wechat_id'],
                    werss_feed_id=row.get('werss_feed_id', '').strip() or None,
                    werss_sync_method='rss',  # 固定为 rss
                    is_active=is_active
                )
                
                db.add(account)
                count += 1
                logger.info(f"Imported: {row['name']}")
            
            db.commit()
            logger.info(f"Successfully imported {count} accounts")
            
    except Exception as e:
        logger.error(f"Failed to import accounts: {str(e)}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: python import_accounts.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not Path(csv_file).exists():
        logger.error(f"File not found: {csv_file}")
        sys.exit(1)
    
    import_accounts(csv_file)


if __name__ == "__main__":
    main()

