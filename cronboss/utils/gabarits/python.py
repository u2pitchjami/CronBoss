#!/usr/bin/env python3
import sys
import logging
from datetime import datetime

# Config logging
log_file = f"/var/log/cronhub/{__file__.split('/')[-1]}.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger()

def main():
    try:
        logger.info("🚀 Début du job")
        
        # --- Ton code ici ---
        # Exemple:
        # subprocess.run(["echo", "Hello"], check=True)

        logger.info("✅ Succès du job")
        return 0
    except Exception as e:
        logger.error(f"❌ Échec du job : {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
