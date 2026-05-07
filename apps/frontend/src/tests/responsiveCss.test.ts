import styles from '../styles.css?raw';

const mobileStyles = styles.slice(styles.indexOf('@media (max-width: 680px)'));

it('reserves mobile navigation space without fixed overlaying feed content', () => {
  expect(mobileStyles).toMatch(/\.left-rail {[\s\S]*position: sticky;/);
  expect(mobileStyles).toMatch(/\.left-rail {[\s\S]*top: 0;/);
  expect(mobileStyles).toMatch(/\.left-rail {[\s\S]*bottom: auto;/);
  expect(mobileStyles).toMatch(/\.left-rail {[\s\S]*grid-template-columns: repeat\(5, minmax\(0, 1fr\)\);/);
});

it('keeps narrow mobile text and controls from forcing horizontal overflow', () => {
  expect(mobileStyles).toMatch(/\.header-chip {[\s\S]*display: none;/);
  expect(mobileStyles).toMatch(/\.post-actions,[\s\S]*\.post-meta,[\s\S]*\.context-line,[\s\S]*\.repost-context {[\s\S]*margin-left: 0;/);
  expect(styles).toMatch(/\.plain-url {[\s\S]*overflow-wrap: anywhere;[\s\S]*word-break: break-word;/);
  expect(styles).toMatch(/\.quote-card\.unavailable {[\s\S]*flex-wrap: wrap;/);
});
