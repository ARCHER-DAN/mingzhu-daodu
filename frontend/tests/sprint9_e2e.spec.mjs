/**
 * Sprint 9 E2E 测试 (S9-02)
 * 测试范围: 注册 / 登录 / 章节阅读 / AI 对话 / 作品切换 / TTS 朗读
 * 运行: npx playwright test tests/sprint9_e2e.spec.mjs
 *
 * 前置条件: 生产服务器 serve_frontend.py 已在 :8080 运行
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
  await page.waitForSelector('#login-email', { timeout: 10000 });
  await page.fill('#login-email', TEST_USER.email);
  await page.fill('#login-password', TEST_USER.password);
  await page.click('button[type="submit"]');
  await page.waitForSelector('.chat-panel', { timeout: 15000 });
}

async function sendQuery(page, query) {
  const input = page.locator('input[aria-label="输入消息"]');
  await input.fill(query);
  await page.keyboard.press('Enter');
  await page.waitForFunction(() => {
    const el = document.querySelector('input[aria-label="输入消息"]');
    return el && el.value === '';
  }, { timeout: 15000 });
}

async function waitForAIResponse(page, timeoutMs = 60000) {
  await page.waitForFunction(() => {
    const msgs = document.querySelectorAll('.msg.ai .msg-text');
    if (msgs.length === 0) return false;
    const last = msgs[msgs.length - 1];
    return last.textContent.trim().length > 10;
  }, { timeout: timeoutMs });
}

// ==================== 用户认证 ====================

test.describe('用户认证', () => {

  test('E2E-01: 注册新用户', async ({ page }) => {
    const testEmail = `e2e_${Date.now()}@test.com`;
    const testName = `测试${Math.floor(Math.random() * 9000) + 1000}`;
    const testPassword = 'TestPass123';

    await page.goto(BASE);
    await page.waitForSelector('#login-email', { timeout: 10000 });

    // 验证在登录页
    await expect(page.locator('h2')).toContainText('登录');

    // 切换到注册模式
    await page.locator('.link-btn:has-text("去注册")').click();
    await expect(page.locator('h2')).toContainText('创建账号');
    await expect(page.locator('#login-name')).toBeVisible();

    // 填写注册信息
    await page.fill('#login-email', testEmail);
    await page.fill('#login-password', testPassword);
    await page.fill('#login-name', testName);

    // 提交注册
    await page.click('button[type="submit"]');

    // 验证进入主界面（注册成功自动登录）
    await page.waitForSelector('.chat-panel', { timeout: 15000 });
    await expect(page.locator('.chat-panel')).toBeVisible();
    await expect(page.locator('.header h1')).toContainText('名著导读');

    // 验证用户名显示在右上角
    await expect(page.locator('.header-controls .user-name')).toContainText(testName);

    console.log(`  [INFO] E2E-01 注册成功: ${testEmail}`);
  });

  test('E2E-02: 登录已有用户', async ({ page }) => {
    await login(page);

    // 验证进入主界面
    await expect(page.locator('.chat-panel')).toBeVisible();
    await expect(page.locator('.header h1')).toContainText('名著导读');

    // 验证用户信息显示
    const userName = page.locator('.header-controls .user-name');
    await expect(userName).toBeVisible();
    const nameText = await userName.textContent();
    expect(nameText.length).toBeGreaterThan(0);

    // 验证左侧阅读面板和对话面板同时存在（双栏布局）
    await expect(page.locator('.reader-panel')).toBeVisible();
    await expect(page.locator('.chat-panel')).toBeVisible();
  });

});

// ==================== 章节阅读 ====================

test.describe('章节阅读', () => {

  test('E2E-03: 浏览章节并阅读正文', async ({ page }) => {
    await login(page);

    // 等待章节列表加载
    await page.waitForSelector('select[aria-label="选择章节"]', { timeout: 15000 });

    // 验证默认选中西游记
    const workSelect = page.locator('select[aria-label="选择名著"]');
    await expect(workSelect).toHaveValue('西游记');

    // 验证章节下拉有选项
    const chapterSelect = page.locator('select[aria-label="选择章节"]');
    const options = await chapterSelect.locator('option').count();
    expect(options).toBeGreaterThan(1); // 占位符 + 至少一个章节

    // 选择第1回
    await chapterSelect.selectOption('0');
    await page.waitForTimeout(2000);

    // 验证章节标题加载
    const chapterTitle = page.locator('.chapter-title');
    await expect(chapterTitle).toBeVisible({ timeout: 10000 });
    const titleText = await chapterTitle.textContent();
    expect(titleText).toContain('第1回');
    expect(titleText.length).toBeGreaterThan(5);

    // 验证正文段落
    const paragraphs = page.locator('.chapter-text p');
    const paraCount = await paragraphs.count();
    expect(paraCount).toBeGreaterThan(0);

    // 验证第一段有实际内容
    const firstPara = await paragraphs.first().textContent();
    expect(firstPara.trim().length).toBeGreaterThan(0);

    // 验证上下回导航按钮存在
    const prevBtn = page.locator('.chapter-nav button[title="上一回"]');
    const nextBtn = page.locator('.chapter-nav button[title="下一回"]');
    await expect(prevBtn).toBeVisible();
    await expect(nextBtn).toBeVisible();

    console.log(`  [PASS] E2E-03 第1回加载成功，${paraCount} 个段落`);
  });

});

// ==================== AI 对话 ====================

test.describe('AI 对话', () => {

  test('E2E-04: 发送对话消息并接收 AI 回复', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(1000);

    // 发送一条测试消息
    const testQuery = '西游记的作者是谁？';
    await sendQuery(page, testQuery);

    // 等待 AI 回复
    await waitForAIResponse(page, 60000);

    // 验证至少有一条用户消息和一条 AI 消息
    const userMsgs = page.locator('.msg.user');
    const aiMsgs = page.locator('.msg.ai');

    await expect(userMsgs.first()).toBeVisible();
    await expect(aiMsgs.first()).toBeVisible();

    // 验证用户消息内容正确
    const userText = await userMsgs.first().locator('.msg-text').textContent();
    expect(userText).toBe(testQuery);

    // 验证 AI 回复有内容且长度合理
    const aiText = await aiMsgs.first().locator('.msg-text').textContent();
    expect(aiText.trim().length).toBeGreaterThan(10);

    // PASS / WEAK / FAIL 评级
    const hasCorrectAnswer = /吴承恩/.test(aiText);
    const hasCitation = /回|章|卷|原文|记载|据/.test(aiText);

    if (hasCorrectAnswer && hasCitation) {
      console.log('  [PASS] E2E-04 回答准确且有出处标注');
    } else if (hasCorrectAnswer) {
      console.log('  [WEAK] E2E-04 回答准确但缺少出处标注');
    } else {
      console.log('  [FAIL] E2E-04 回答可能不准确或为幻觉');
    }

    // 验证点赞/点踩按钮存在
    const likeBtn = aiMsgs.first().locator('button[aria-label="点赞"]');
    const dislikeBtn = aiMsgs.first().locator('button[aria-label="点踩"]');
    await expect(likeBtn).toBeVisible();
    await expect(dislikeBtn).toBeVisible();
  });

});

// ==================== 作品切换 ====================

test.describe('作品切换', () => {

  test('E2E-05: 切换作品并验证章节列表更新', async ({ page }) => {
    await login(page);

    const workSelect = page.locator('select[aria-label="选择名著"]');
    await expect(workSelect).toHaveValue('西游记');

    // 等待章节列表加载
    await page.waitForSelector('select[aria-label="选择章节"]', { timeout: 15000 });
    const xyOptions = await page.locator('select[aria-label="选择章节"] option').count();

    // 切换到三国演义
    await workSelect.selectOption('三国演义');
    await page.waitForTimeout(1500);
    await expect(workSelect).toHaveValue('三国演义');

    // 验证章节列表已更新且可见
    const chapterSelect = page.locator('select[aria-label="选择章节"]');
    await expect(chapterSelect).toBeVisible({ timeout: 10000 });
    const sgOptions = await chapterSelect.locator('option').count();
    expect(sgOptions).toBeGreaterThan(1);
    console.log(`  西游记: ${xyOptions} options, 三国演义: ${sgOptions} options`);

    // 切换到红楼梦
    await workSelect.selectOption('红楼梦');
    await page.waitForTimeout(1500);
    await expect(workSelect).toHaveValue('红楼梦');
    await expect(page.locator('select[aria-label="选择章节"]')).toBeVisible({ timeout: 10000 });

    // 切换到水浒传
    await workSelect.selectOption('水浒传');
    await page.waitForTimeout(1500);
    await expect(workSelect).toHaveValue('水浒传');
    await expect(page.locator('select[aria-label="选择章节"]')).toBeVisible({ timeout: 10000 });

    // 切回西游记——确认能切回
    await workSelect.selectOption('西游记');
    await page.waitForTimeout(1500);
    await expect(workSelect).toHaveValue('西游记');
    await expect(page.locator('select[aria-label="选择章节"]')).toBeVisible({ timeout: 10000 });

    console.log('  [PASS] E2E-05 四部名著切换全部正常');
  });

});

// ==================== TTS 朗读 ====================

test.describe('TTS 朗读', () => {

  test('E2E-06: TTS 播放按钮存在且可交互', async ({ page }) => {
    await login(page);

    // 等待章节列表并选择章节
    await page.waitForSelector('select[aria-label="选择章节"]', { timeout: 15000 });
    await page.locator('select[aria-label="选择章节"]').selectOption('0');
    await page.waitForSelector('.chapter-title', { timeout: 10000 });
    await page.waitForTimeout(1000);

    // 验证 TTS 按钮存在（章节加载后才渲染）
    const ttsBtn = page.locator('.tts-btn');
    await expect(ttsBtn).toBeVisible({ timeout: 5000 });

    // 验证按钮有 title/文本（播放、暂停、继续之一）
    const btnTitle = await ttsBtn.getAttribute('title');
    expect(btnTitle).toBeTruthy();

    // 尝试点击播放按钮
    await ttsBtn.click();
    await page.waitForTimeout(1000);

    // headless 模式下 speechSynthesis 不可用，页面不应崩溃
    await expect(page.locator('.chat-panel')).toBeVisible();
    await expect(page.locator('.reader-panel')).toBeVisible();

    // 验证 TTS 进度条存在
    const progressWrap = page.locator('.tts-progress-wrap');
    await expect(progressWrap).toBeVisible();

    // 如果有停止按钮则点击停止
    const stopBtn = page.locator('.tts-stop');
    if (await stopBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await stopBtn.click();
      await page.waitForTimeout(500);
    }

    console.log('  [INFO] E2E-06 TTS 按钮+进度条存在且可交互（headless 下 speechSynthesis 不可用属预期）');
  });

});

// ==================== 边界与异常 ====================

test.describe('边界与异常', () => {

  test('E2E-07: 登录失败 — 错误密码', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('#login-email', { timeout: 10000 });

    await page.fill('#login-email', TEST_USER.email);
    await page.fill('#login-password', 'WrongPassword999');
    await page.click('button[type="submit"]');

    // 应显示错误提示
    await expect(page.locator('.login-error')).toBeVisible({ timeout: 5000 });
    const errorText = await page.locator('.login-error').textContent();
    expect(errorText.length).toBeGreaterThan(0);

    // 应仍在登录页
    await expect(page.locator('h2')).toContainText('登录');
    await expect(page.locator('#login-email')).toBeVisible();
  });

  test('E2E-08: 注册失败 — 重复邮箱', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForSelector('#login-email', { timeout: 10000 });

    // 切换到注册模式
    await page.locator('.link-btn:has-text("去注册")').click();
    await expect(page.locator('h2')).toContainText('创建账号');

    // 用已有邮箱注册
    await page.fill('#login-email', TEST_USER.email);
    await page.fill('#login-password', 'SomePass123');
    await page.fill('#login-name', '重复用户');
    await page.click('button[type="submit"]');

    // 应显示错误
    await expect(page.locator('.login-error')).toBeVisible({ timeout: 5000 });
    const errorText = await page.locator('.login-error').textContent();
    console.log(`  [INFO] E2E-08 重复邮箱错误提示: ${errorText}`);
  });

  test('E2E-09: 退出登录返回登录页', async ({ page }) => {
    await login(page);
    await expect(page.locator('.chat-panel')).toBeVisible();

    // 点击退出按钮
    await page.locator('.logout-btn').click();

    // 应返回登录页
    await page.waitForSelector('#login-email', { timeout: 10000 });
    await expect(page.locator('h2')).toContainText('登录');

    // 验证 token 已清除
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeNull();
  });

  test('E2E-10: 推荐问题点击自动发送', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(1000);

    // 如果没有对话则在欢迎页
    const welcome = page.locator('.welcome');
    await expect(welcome).toBeVisible({ timeout: 5000 });

    // 点击第一个推荐问题
    const questionChip = page.locator('.q-chip').first();
    await expect(questionChip).toBeVisible();
    const questionText = await questionChip.textContent();
    await questionChip.click();

    // 应出现用户消息
    await expect(page.locator('.msg.user')).toBeVisible({ timeout: 10000 });
    const userMsg = await page.locator('.msg.user .msg-text').first().textContent();
    expect(userMsg).toBe(questionText.trim());

    // 等待 AI 回复
    await waitForAIResponse(page, 60000);
    const aiMsg = await page.locator('.msg.ai .msg-text').first().textContent();
    expect(aiMsg.trim().length).toBeGreaterThan(10);

    console.log(`  [PASS] E2E-10 推荐问题「${questionText.trim()}」→ AI 已回复`);
  });

});

// ==================== 综合场景 ====================

test.describe('综合场景', () => {

  test('E2E-11: 完整用户旅程 — 登录→阅读→提问→切换作品', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(1000);

    // 1. 选择章节阅读
    await page.waitForSelector('select[aria-label="选择章节"]', { timeout: 15000 });
    await page.locator('select[aria-label="选择章节"]').selectOption('0');
    await page.waitForSelector('.chapter-title', { timeout: 10000 });
    const titleText = await page.locator('.chapter-title').textContent();
    expect(titleText).toContain('第1回');

    // 2. 发送问题
    await sendQuery(page, '这一回的主要内容是什么？');
    await waitForAIResponse(page, 60000);
    const aiTextFirst = await page.locator('.msg.ai .msg-text').last().textContent();
    expect(aiTextFirst.trim().length).toBeGreaterThan(10);

    // 3. 切换到三国演义
    await page.locator('select[aria-label="选择名著"]').selectOption('三国演义');
    await page.waitForTimeout(1500);
    await expect(page.locator('select[aria-label="选择名著"]')).toHaveValue('三国演义');

    // 4. 验证三国演义章节列表
    await page.waitForSelector('select[aria-label="选择章节"]', { timeout: 10000 });
    const sgChapters = await page.locator('select[aria-label="选择章节"] option').count();
    expect(sgChapters).toBeGreaterThan(1);

    // 5. 在三国演义选择章节阅读
    await page.locator('select[aria-label="选择章节"]').selectOption('0');
    await page.waitForSelector('.chapter-title', { timeout: 10000 });
    const sgTitle = await page.locator('.chapter-title').textContent();
    expect(sgTitle.length).toBeGreaterThan(5);

    // 6. 在三国演义下发问题
    await sendQuery(page, '请简介本章内容');
    await waitForAIResponse(page, 60000);
    const aiTextSecond = await page.locator('.msg.ai .msg-text').last().textContent();
    expect(aiTextSecond.trim().length).toBeGreaterThan(10);

    // 7. 页面不崩溃
    await expect(page.locator('.chat-panel')).toBeVisible();
    await expect(page.locator('.reader-panel')).toBeVisible();

    console.log('  [PASS] E2E-11 完整旅程通过');
  });

});
