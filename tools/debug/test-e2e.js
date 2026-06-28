// e2e-test.js - 端到端测试脚本
const { chromium } = require('playwright')

async function runTest() {
  const browser = await chromium.launch({ headless: false })
  const context = await browser.newContext()
  const page = await context.newPage()

  let passed = 0
  let failed = 0
  const errors = []

  async function check(label, fn) {
    try {
      await fn()
      console.log(`  ✅ ${label}`)
      passed++
    } catch (e) {
      console.log(`  ❌ ${label}: ${e.message}`)
      errors.push({ label, error: e.message })
      failed++
    }
  }

  console.log('\n🧪 开始端到端测试...\n')

  // ========== 1. 首页加载 ==========
  console.log('📋 1. 首页加载')
  await page.goto('http://localhost:3002/')
  await check('页面标题正确', async () => {
    await page.waitForSelector('h1', { timeout: 5000 })
    const title = await page.textContent('h1')
    if (!title.includes('视频智能分析')) throw new Error(`标题不符: ${title}`)
  })

  await check('URL 输入框存在', async () => {
    const input = await page.$('input[type="url"], input[placeholder*="视频链接"]')
    if (!input) throw new Error('未找到输入框')
  })

  await check('支持平台标签显示', async () => {
    const body = await page.textContent('body')
    if (!body.includes('B站') || !body.includes('抖音') || !body.includes('YouTube'))
      throw new Error('平台标签缺失')
  })

  // ========== 2. 提交视频 URL ==========
  console.log('\n📋 2. 提交视频 URL')
  const testUrl = 'https://v.douyin.com/HioEUeExwR0/'

  await check('输入 URL 并提交', async () => {
    await page.fill('input[type="url"]', testUrl)
    await page.click('button[type="submit"]')
    // 等待进度条或错误提示出现（最多 10 秒）
    await page.waitForSelector('.progress, [class*="progress"], .error, [role="progressbar"]', { timeout: 10000 })
  })

  // 等待一下让请求完成
  await page.waitForTimeout(2000)

  await check('进度条或任务状态显示', async () => {
    const body = await page.textContent('body')
    const hasProgress = body.includes('步骤') || body.includes('下载') || body.includes('分析') || body.includes('提交中')
    if (!hasProgress) throw new Error('未显示进度信息')
  })

  // 获取 task_id（从页面或 WS 消息中）
  let taskId = null
  try {
    taskId = await page.evaluate(() => {
      // 尝试从页面中获取 task_id
      const el = document.querySelector('[data-task-id]')
      return el ? el.dataset.taskId : null
    })
    console.log(`  ℹ️ 当前 task_id: ${taskId || '(无法获取)'}`)
  } catch {}

  // ========== 3. 视频列表页 ==========
  console.log('\n📋 3. 视频列表页')
  await page.goto('http://localhost:3002/videos')
  await page.waitForTimeout(2000)

  await check('视频列表页加载', async () => {
    const body = await page.textContent('body')
    if (!body) throw new Error('页面为空')
  })

  await check('API /api/videos 可访问', async () => {
    const resp = await page.evaluate(async () => {
      const r = await fetch('/api/videos')
      return { status: r.status, ok: r.ok }
    })
    if (!resp.ok) throw new Error(`API 返回 ${resp.status}`)
  })

  // ========== 4. 知识库搜索页 ==========
  console.log('\n📋 4. 知识库搜索页')
  await page.goto('http://localhost:3002/knowledge')
  await page.waitForTimeout(2000)

  await check('知识库页面加载', async () => {
    const body = await page.textContent('body')
    if (!body) throw new Error('页面为空')
  })

  await check('搜索输入框存在', async () => {
    const hasInput = await page.$('input[type="text"], input[placeholder*="搜索"]')
    if (!hasInput) throw new Error('未找到搜索框')
  })

  // ========== 5. 批量处理页 ==========
  console.log('\n📋 5. 批量处理页')
  await page.goto('http://localhost:3002/batch')
  await page.waitForTimeout(2000)

  await check('批量处理页加载', async () => {
    const body = await page.textContent('body')
    if (!body) throw new Error('页面为空')
  })

  await check('多 URL 输入框存在', async () => {
    const hasTextarea = await page.$('textarea, input[placeholder*="URL"]')
    if (!hasTextarea) throw new Error('未找到多行输入框')
  })

  // ========== 6. API 端点测试 ==========
  console.log('\n📋 6. 后端 API 测试')

  await check('GET /api/stats 正常', async () => {
    const resp = await page.evaluate(async () => {
      const r = await fetch('/api/stats')
      return { status: r.status, data: await r.json() }
    })
    if (resp.status !== 200) throw new Error(`返回 ${resp.status}`)
  })

  await check('WebSocket 端点可连接', async () => {
    const result = await page.evaluate(() => {
      return new Promise((resolve) => {
        const ws = new WebSocket('ws://localhost:3002/ws/tasks/999999')
        ws.onopen = () => { ws.close(); resolve({ ok: true }) }
        ws.onerror = (e) => resolve({ ok: false, error: '连接失败' })
        setTimeout(() => { ws.close(); resolve({ ok: false, error: '超时' }) }, 3000)
      })
    })
    if (!result.ok) throw new Error(result.error)
  })

  // ========== 7. 导航栏 ==========
  console.log('\n📋 7. 导航栏链接')
  await page.goto('http://localhost:3002/')

  await check('导航栏包含视频库链接', async () => {
    const links = await page.$$('a[href*="/videos"]')
    if (links.length === 0) throw new Error('未找到视频库链接')
  })

  await check('导航栏包含知识库链接', async () => {
    const links = await page.$$('a[href*="/knowledge"]')
    if (links.length === 0) throw new Error('未找到知识库链接')
  })

  await check('导航栏包含批量处理链接', async () => {
    const links = await page.$$('a[href*="/batch"]')
    if (links.length === 0) throw new Error('未找到批量处理链接')
  })

  // ========== 结果汇总 ==========
  console.log('\n' + '='.repeat(40))
  console.log(`\n✅ 通过: ${passed}   ❌ 失败: ${failed}\n`)
  if (errors.length > 0) {
    console.log('失败详情:')
    errors.forEach(({ label, error }) => console.log(`  - ${label}: ${error}`))
  }
  console.log('='.repeat(40) + '\n')

  await browser.close()
  process.exit(failed > 0 ? 1 : 0)
}

runTest().catch(e => {
  console.error('测试运行失败:', e)
  process.exit(1)
})
