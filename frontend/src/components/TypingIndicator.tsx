"use client";

import styles from "./TypingIndicator.module.css";

export default function TypingIndicator() {
  return (
    <div className={styles.container}>
      <div className={styles.bubble}>
        <div className={styles.dots}>
          <span className={styles.dot} />
          <span className={styles.dot} />
          <span className={styles.dot} />
        </div>
      </div>
    </div>
  );
}
