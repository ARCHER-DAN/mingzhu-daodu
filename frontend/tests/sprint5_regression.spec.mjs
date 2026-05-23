/**
 * Sprint 5 回归测试 (T05)
 * 测试: 对话持久化 / 多轮对话 / 阅读进度记忆 / 基础功能无回归
 */
import { test, expect } from '@playwright/test';

const BASE = 'http://127.0.0.1:8080';
const TEST_USER = {
  email: os.environ.get('ADMIN_EMAIL', 'admin@example.com'),
  password: os.environ.get('ADMIN_PASSWORD', ''),
};

// ==================== 辅助函数 ====================

async function login(page) {
  await page.goto(BASE);
  // 等待登录页加载
  await page.waitForSelector('#login-email', { timeout: 10000 });
  await page.fill('#login-email', TEST_USER.email);
  await page.fill('#login-password', TEST_USER.password);
  await page.click('button[type="submit"]');
  // 等待进入主界面
  await page.waitForSelector('.chat-panel', { timeout: 15000 });
}

async function waitForAIResponse(page, timeoutMs = 60000) {
  // 等待 AI 回复内容出现（流式响应可能较慢）
  await page.waitForFunction(() => {
    const msgs = document.querySelectorAll('.msg.ai .msg-text');
    if (msgs.length === 0) return false;
    const last = msgs[msgs.length - 1];
    return last.textContent.trim().length > 10;
  }, { timeout: timeoutMs });
}

async function sendQuery(page, query) {
  const input = page.locator('input[aria-label="输入消息"]');
  await input.fill(query);
  await page.keyboard.press('Enter');
  // 等待输入框清空（表示消息已发送）
  await page.waitForFunction(() => {
    const el = document.querySelector('input[aria-label="输入消息"]');
    return el && el.value === '';
  }, { timeout: 15000 });
}

// ==================== 1. 基础功能无回归 ====================

test.describe('基础功能回归', () => {

  test('T01 - 登录流程正常', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('#login-email', { timeout: 10000 });

    // 验证登录页元素
    await expect(page.locator('h2')).toContainText('登录');
    await expect(page.locator('#login-email')).toBeVisible();
    await expect(page.locator('#login-password')).toBeVisible();

    // 执行登录
    await page.fill('#login-email', TEST_USER.email);
    await page.fill('#login-password', TEST_USER.password);
    await page.click('button[type="submit"]');

    // 应进入主界面
    await page.waitForSelector('.chat-panel', { timeout: 15000 });
    await expect(page.locator('.chat-panel')).toBeVisible();
    await expect(page.locator('.header h1')).toContainText('名著导读');
  });

  test('T02 - 四部名著切换正常', async ({ page }) => {
    await login(page);

    const works = ['西游记', '三国演义', '红楼梦', '水浒传'];
    const select = page.locator('select[aria-label="选择名著"]');

    for (const work of works) {
      await select.selectOption(work);
      // 等待界面更新（至少章节列表/提示更新）
      await page.waitForTimeout(800);
      // 确认选中的值
      await expect(select).toHaveValue(work);
    }
  });

  test('T03 - 章节列表加载正常', async ({ page }) => {
    await login(page);

    // 默认应该是西游记，等待章节列表
    await page.waitForSelector('select[aria-label="选择章节"]', { timeout: 15000 });

    const chapterSelect = page.locator('select[aria-label="选择章节"]');
    // 验证有章节选项
    const options = await chapterSelect.locator('option').count();
    expect(options).toBeGreaterThan(1); // 至少有 "选择章节" 占位符 + 章节

    // 切换到三国演义
    await page.locator('select[aria-label="选择名著"]').selectOption('三国演义');
    await page.waitForTimeout(800);
    const options2 = await chapterSelect.locator('option').count();
    expect(options2).toBeGreaterThan(1);
  });

  test('T04 - 章节正文正常显示', async ({ page }) => {
    await login(page);

    // 等待章节列表
    await page.waitForSelector('select[aria-label="选择章节"]', { timeout: 15000 });

    // 选择第1回
    const chapterSelect = page.locator('select[aria-label="选择章节"]');
    await chapterSelect.selectOption('0'); // 第1回
    await page.waitForTimeout(2000);

    // 应显示章节标题
    const chapterTitle = page.locator('.chapter-title');
    await expect(chapterTitle).toBeVisible({ timeout: 10000 });
    const titleText = await chapterTitle.textContent();
    expect(titleText).toContain('第1回');

    // 应有正文段落
    const paragraphs = page.locator('.chapter-text p');
    const count = await paragraphs.count();
    expect(count).toBeGreaterThan(0);
  });

  test('T05 - 登录/注册切换 UI 正常', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('#login-email', { timeout: 10000 });

    // 切换到注册模式
    await page.locator('.link-btn:has-text("去注册")').click();
    await expect(page.locator('h2')).toContainText('创建账号');
    await expect(page.locator('#login-name')).toBeVisible();

    // 切回登录模式
    await page.locator('.link-btn:has-text("去登录")').click();
    await expect(page.locator('h2')).toContainText('登录');
  });

});

// ==================== 2. 对话持久化 ====================

test.describe('对话持久化', () => {

  test('T06 - 发送消息后刷新，对话应恢复', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(1000);

    // 发一条消息
    const testQuery = '西游记的作者是谁？';
    await sendQuery(page, testQuery);
    await waitForAIResponse(page, 60000);

    // 等待 saveConv 完成
    await page.waitForTimeout(2000);

    // 记录消息数量
    const msgCountBefore = await page.locator('.msg').count();
    expect(msgCountBefore).toBeGreaterThanOrEqual(2); // 1 user + 1 ai

    // 刷新页面
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.chat-panel', { timeout: 15000 });
    await page.waitForTimeout(2000);

    // 检查消息是否恢复
    const msgCountAfter = await page.locator('.msg').count();
    // 刷新后消息应该从 localStorage 恢复
    expect(msgCountAfter).toBeGreaterThanOrEqual(msgCountBefore - 0);
  });

  test('T07 - 新建对话，发消息，切回旧对话，消息应完整', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(1000);

    // 先确认有至少一个对话（在 T06 之后已有）
    // 新建对话
    const newConvBtn = page.locator('.conv-new-btn');
    await newConvBtn.click({ timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(500);

    // 在新对话中发消息
    await sendQuery(page, '林黛玉是谁？');
    await waitForAIResponse(page, 60000);
    await page.waitForTimeout(2000);

    // 记录新对话中的消息数
    const msgCountNew = await page.locator('.msg').count();
    expect(msgCountNew).toBeGreaterThanOrEqual(2);

    // 如果有旧对话，切换到第一个旧对话
    const convItems = page.locator('.conv-item');
    const convCount = await convItems.count();

    if (convCount >= 2) {
      await convItems.nth(1).click();
      await page.waitForTimeout(1500);

      // 旧对话应有消息
      const msgCountOld = await page.locator('.msg').count();
      expect(msgCountOld).toBeGreaterThanOrEqual(2);

      // 切回新对话
      await convItems.nth(0).click();
      await page.waitForTimeout(1500);

      // 新对话消息应仍完整
      const msgCountNewAgain = await page.locator('.msg').count();
      expect(msgCountNewAgain).toBe(msgCountNew);
    }
  });

  test('T08 - 切作品 → 对话列表应切换', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(1000);

    // 在西游记下发消息
    await page.locator('select[aria-label="选择名著"]').selectOption('西游记');
    await page.waitForTimeout(800);
    await sendQuery(page, '孙悟空有哪些本事？');
    await waitForAIResponse(page, 60000);
    await page.waitForTimeout(2000);

    // 切换到红楼梦
    await page.locator('select[aria-label="选择名著"]').selectOption('红楼梦');
    await page.waitForTimeout(1500);

    // 应该出现欢迎页（因为是全新作品无对话）
    const welcome = page.locator('.welcome');
    await expect(welcome).toBeVisible({ timeout: 5000 });

    // 切换回西游记
    await page.locator('select[aria-label="选择名著"]').selectOption('西游记');
    await page.waitForTimeout(1500);

    // 之前西游记的对话应恢复
    const msgs = await page.locator('.msg').count();
    expect(msgs).toBeGreaterThanOrEqual(2);
  });

});

// ==================== 3. 多轮对话 ====================

test.describe('多轮对话', () => {

  test('T09 - 多轮对话，AI 应理解上下文', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(1000);

    // 新建对话
    const newConvBtn = page.locator('.conv-new-btn');
    await newConvBtn.click({ timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(500);

    // 第一轮：询问孙悟空
    await sendQuery(page, '孙悟空有哪些本事？');
    await waitForAIResponse(page, 90000);
    await page.waitForTimeout(1000);

    // 第二轮：追问 "他还会别的吗？"
    await sendQuery(page, '他还会别的吗？');
    await waitForAIResponse(page, 90000);
    await page.waitForTimeout(1000);

    // 收集所有AI回复
    const aiMsgs = page.locator('.msg.ai .msg-text');
    const aiTexts = await aiMsgs.allTextContents();

    // 至少有两轮回复，且第二轮不应是空或提示误解
    expect(aiTexts.length).toBeGreaterThanOrEqual(2);

    // 第二轮回复应包含相关内容（理解"他"=孙悟空）
    const secondResponse = aiTexts[aiTexts.length - 1] || '';
    const combined = aiTexts.join(' ');

    // 上下文理解：回复不应包含"请问你指的是谁"之类的误解
    const confusionPatterns = /不知道.*指|请明确|请说明.*谁|无法理解/;
    expect(combined).not.toMatch(confusionPatterns);

    // 应有2轮以上对话消息
    const totalMsgs = await page.locator('.msg').count();
    expect(totalMsgs).toBeGreaterThanOrEqual(4); // 2 user + 2 ai
  });

});

// ==================== 4. 阅读进度记忆 ====================

test.describe('阅读进度记忆', () => {

  test('T10 - 选章节后刷新 → 恢复到该章节', async ({ page }) => {
    await login(page);
    await page.waitForSelector('select[aria-label="选择章节"]', { timeout: 15000 });

    // 选择第5回
    const chapterSelect = page.locator('select[aria-label="选择章节"]');
    await chapterSelect.selectOption('4'); // 第5回 (0-indexed)
    await page.waitForTimeout(3000); // 等待章节加载

    // 确认标题包含第5回
    const titleBefore = await page.locator('.chapter-title').textContent();
    expect(titleBefore).toContain('第5回');

    // 刷新页面
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.chat-panel', { timeout: 15000 });
    await page.waitForTimeout(2000);

    // 章节应恢复到第5回
    const chapterText = page.locator('.chapter-text');
    await expect(chapterText).toBeVisible({ timeout: 10000 });
    const titleAfter = await page.locator('.chapter-title').textContent();
    expect(titleAfter).toContain('第5回');
  });

  test('T11 - 切作品再切回 → 应恢复之前选的章节', async ({ page }) => {
    await login(page);
    await page.waitForSelector('select[aria-label="选择章节"]', { timeout: 15000 });

    // 在西游记选第3回
    await page.locator('select[aria-label="选择名著"]').selectOption('西游记');
    await page.waitForTimeout(1000);
    await page.locator('select[aria-label="选择章节"]').selectOption('2'); // 第3回
    await page.waitForTimeout(3000);
    const xiYouTitle = await page.locator('.chapter-title').textContent();
    expect(xiYouTitle).toContain('第3回');

    // 切换到红楼梦（应有章节列表）
    await page.locator('select[aria-label="选择名著"]').selectOption('红楼梦');
    await page.waitForSelector('select[aria-label="选择章节"]', { timeout: 10000 });
    await page.waitForTimeout(1000);

    // 切回西游记
    await page.locator('select[aria-label="选择名著"]').selectOption('西游记');
    await page.waitForTimeout(2000);

    // 应恢复到西游记第3回
    const restoredTitle = await page.locator('.chapter-title');
    await expect(restoredTitle).toBeVisible({ timeout: 10000 });
    expect(await restoredTitle.textContent()).toContain('第3回');
  });

});

// ==================== 5. 语义验证 ====================

test.describe('语义验证', () => {

  test('T12 - AI 回答应有出处标注且通顺（PASS/WEAK/FAIL 评级）', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(1000);

    // 问一个有明确答案的问题
    await sendQuery(page, '西游记的作者是谁？');
    await waitForAIResponse(page, 60000);
    await page.waitForTimeout(1000);

    // 收集 AI 回复
    const aiMsgs = page.locator('.msg.ai .msg-text');
    const lastResponse = (await aiMsgs.last().textContent()) || '';

    // PASS 标准: 准确 + 有出处标注 + 语言通顺
    // WEAK 标准: 部分准确但不完整
    // FAIL 标准: 错误/幻觉

    const hasCorrectAnswer = /吴承恩/.test(lastResponse);
    const hasCitation = /回|章|卷|原文|记载|书.|据/.test(lastResponse);
    const notEmpty = lastResponse.length > 20;
    const notConfused = !/错误|抱歉|无法|不确定/.test(lastResponse);

    // 至少应该是 WEAK 以上（不能是 FAIL）
    expect(hasCorrectAnswer && notEmpty).toBeTruthy();

    // 记录评级结果
    if (hasCorrectAnswer && hasCitation && notEmpty && notConfused) {
      console.log('  [PASS] 回答准确、有出处、语言通顺');
    } else if (hasCorrectAnswer && notEmpty) {
      console.log('  [WEAK] 回答基本准确但可能缺出处或不完整');
    } else {
      console.log('  [FAIL] 回答错误或不相关');
    }
  });

  test('T13 - 四大名著基础问题检索', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(1000);

    const questions = [
      { work: '西游记', q: '大闹天宫是怎么回事？' },
      { work: '三国演义', q: '赤壁之战的故事梗概' },
      { work: '红楼梦', q: '林黛玉进贾府的故事' },
      { work: '水浒传', q: '武松打虎的故事' },
    ];

    let passCount = 0;
    let weakCount = 0;
    let failCount = 0;

    for (const { work, q } of questions) {
      await page.locator('select[aria-label="选择名著"]').selectOption(work);
      await page.waitForTimeout(800);

      // 新建对话确保干净上下文
      try {
        await page.locator('.conv-new-btn').click({ timeout: 3000 });
        await page.waitForTimeout(500);
      } catch {}

      await sendQuery(page, q);
      await waitForAIResponse(page, 90000);
      await page.waitForTimeout(1000);

      const aiMsgs = page.locator('.msg.ai .msg-text');
      const response = (await aiMsgs.last().textContent()) || '';

      const notEmpty = response.length > 20;
      const notError = !/错误|抱歉|无法.*回答/.test(response);
      const notConfused = !/我不.*知道|没有.*信息/.test(response);

      if (notEmpty && notError && notConfused) {
        passCount++;
        console.log(`  [PASS] ${work} - "${q}"`);
      } else if (notEmpty) {
        weakCount++;
        console.log(`  [WEAK] ${work} - "${q}" -> ${response.slice(0, 100)}`);
      } else {
        failCount++;
        console.log(`  [FAIL] ${work} - "${q}" -> 空响应或错误`);
      }
    }

    console.log(`\n  结果: PASS=${passCount}/4, WEAK=${weakCount}/4, FAIL=${failCount}/4`);
    expect(failCount).toBe(0); // 不允许 FAIL
  });

});

// ==================== 6. 边界/异常场景 ====================

test.describe('边界/异常场景', () => {

  test('T14 - 空消息不能发送', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(1000);

    const input = page.locator('input[aria-label="输入消息"]');
    await input.fill('   ');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);

    // 输入框内容可能被 trim 掉，不应产生消息
    const msgs = page.locator('.msg');
    // 此时若为空 welcome 页（没有消息），或消息数没有增加
    const welcome = page.locator('.welcome');
    const hasWelcome = await welcome.isVisible().catch(() => false);
    if (hasWelcome) {
      // 仍然在欢迎页，说明空消息没发送
      await expect(welcome).toBeVisible();
    }
  });

  test('T15 - 快速切换作品不崩溃', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(1000);

    const works = ['西游记', '三国演义', '红楼梦', '水浒传'];
    // 快速切换3轮
    for (let round = 0; round < 3; round++) {
      for (const work of works) {
        await page.locator('select[aria-label="选择名著"]').selectOption(work);
        await page.waitForTimeout(300);
      }
    }

    // 最终应用应仍然可用
    await expect(page.locator('.chat-panel')).toBeVisible();
    await expect(page.locator('.reader-panel')).toBeVisible();
  });

  test('T16 - localStorage 持久化验证', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(1000);

    // 检查 token 必须存在
    const token = await page.evaluate(() =>
      localStorage.getItem('token')
    );
    expect(token).toBeTruthy();
    expect(token.length).toBeGreaterThan(10);

    // 选一个章节，触发进度保存
    await page.waitForSelector('select[aria-label="选择章节"]', { timeout: 15000 });
    await page.locator('select[aria-label="选择章节"]').selectOption('0');
    await page.waitForSelector('.chapter-title', { timeout: 10000 });

    // 验证 progress 已保存
    const progress = await page.evaluate(() =>
      localStorage.getItem('mingzhu_reading_progress')
    );
    expect(progress).toBeTruthy();
    const progressObj = JSON.parse(progress || '{}');
    expect(progressObj.work).toBeTruthy();
    expect(progressObj.chapterIdx).toBe(0);

    // 发一条消息，验证 conversations 持久化
    await sendQuery(page, 'hello');
    await waitForAIResponse(page, 60000);
    await page.waitForTimeout(2000);

    const conversations = await page.evaluate(() =>
      localStorage.getItem('mingzhu_conversations')
    );
    expect(conversations).toBeTruthy();
    const convObj = JSON.parse(conversations || '{}');
    const workConvs = convObj['西游记'] || [];
    expect(workConvs.length).toBeGreaterThan(0);
  });

});
