/**
 * ============================================================================
 * 零售行业经营与贷款智慧风控平台 - 前端主脚本
 * ============================================================================
 *
 * 文件名：main.js
 * 功能：提供全局工具函数、UI交互、数据处理、表单验证等前端核心功能
 *
 * 主要功能模块：
 * 1. 页面初始化 - Bootstrap组件、响应式布局、事件监听
 * 2. 图表响应式处理 - Chart.js图表自适应窗口大小
 * 3. UI交互功能 - 平滑滚动、工具提示、弹出框
 * 4. 表格功能 - 排序、搜索高亮
 * 5. 工具函数 - 数据格式化、AJAX请求、Toast提示、文件导出
 *
 * 技术栈：
 * - Bootstrap 5 - UI框架
 * - Chart.js - 数据可视化
 * - 原生 JavaScript - ES6+语法
 *
 * 作者：零售风控平台开发团队
 * 创建日期：2024年
 * 版本：1.0
 */

// ==================== 全局变量声明 ====================

/**
 * 窗口resize事件的防抖计时器
 * 用于避免频繁触发resize事件导致性能问题
 * @type {number|null}
 */
let resizeTimeout;


// ==================== 页面初始化 ====================

/**
 * DOM内容加载完成后的初始化函数
 * 在页面所有DOM元素加载完毕后自动执行
 * 负责初始化各类组件和事件监听器
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('[初始化] 页面开始加载，初始化各类组件...');

    // 初始化Bootstrap工具提示（tooltip）
    // tooltip是鼠标悬停时显示的小提示框
    initTooltips();

    // 初始化Bootstrap弹出框（popover）
    // popover是点击后显示的弹出式信息框
    initPopovers();

    // 添加页面内锚点链接的平滑滚动效果
    // 提升用户体验，使页面切换更加流畅
    initSmoothScroll();

    // 为所有表格添加排序功能
    // 允许用户点击表头对数据进行升序/降序排列
    initTableSorting();

    // 添加搜索结果高亮功能
    // 用户搜索时，自动高亮匹配的文本内容
    initSearchHighlight();

    // 初始化图表的响应式布局
    // 确保图表在不同屏幕尺寸下都能正常显示
    initChartResponsive();

    // 监听窗口大小变化事件
    // 当用户调整浏览器窗口大小时，自动调整图表等响应式元素
    window.addEventListener('resize', handleWindowResize);

    console.log('[初始化] 页面组件初始化完成');
});


// ==================== 图表响应式处理模块 ====================

/**
 * 初始化所有Chart.js图表的响应式布局
 *
 * 功能说明：
 * 1. 为所有图表容器设置正确的CSS样式（position、width、height）
 * 2. 确保canvas元素是响应式的（max-width: 100%）
 * 3. 配合Chart.js的maintainAspectRatio选项实现自适应
 *
 * 查询选择器说明：
 * - canvas[id^="city"] - 匹配id以"city"开头的canvas（城市分布图表）
 * - canvas[id^="category"] - 匹配id以"category"开头的canvas（分类图表）
 * - canvas[id^="credit"] - 匹配id以"credit"开头的canvas（信用等级图表）
 * - canvas[id^="risk"] - 匹配id以"risk"开头的canvas（风险分析图表）
 * - canvas[id^="business"] - 匹配id以"business"开头的canvas（经营分析图表）
 * - canvas[id^="revenue"] - 匹配id以"revenue"开头的canvas（收入图表）
 */
function initChartResponsive() {
    console.log('[图表] 开始初始化图表响应式布局...');

    // 查找页面中所有的Chart.js图表元素
    const chartCanvases = document.querySelectorAll(
        'canvas[id^="city"], canvas[id^="category"], canvas[id^="credit"], ' +
        'canvas[id^="risk"], canvas[id^="business"], canvas[id^="revenue"]'
    );

    // 遍历每个图表元素进行配置
    chartCanvases.forEach(canvas => {
        // 获取canvas的父容器
        if (canvas.parentElement) {
            // 设置父容器样式
            // position: relative - 确保子元素绝对定位时相对于此容器
            // width: 100% - 容器宽度占满父元素
            // height: auto - 高度自适应内容
            // overflow: hidden - 防止内容溢出
            canvas.parentElement.style.position = 'relative';
            canvas.parentElement.style.width = '100%';
            canvas.parentElement.style.height = 'auto';
            canvas.parentElement.style.overflow = 'hidden';
        }

        // 设置canvas本身的响应式样式
        // max-width: 100% - 最大宽度不超过父容器
        // height: auto - 高度根据宽度比例自动调整
        canvas.style.maxWidth = '100%';
        canvas.style.height = 'auto';
    });

    console.log(`[图表] 已配置 ${chartCanvases.length} 个图表的响应式布局`);
}

/**
 * 处理窗口大小变化事件
 *
 * 功能说明：
 * 1. 使用防抖（debounce）技术，避免窗口大小连续变化时频繁触发resize
 * 2. 延迟250ms后执行实际的resize操作
 * 3. 重新调整所有Chart.js图表的大小
 * 4. 触发自定义事件，通知其他组件窗口已调整
 *
 * 防抖原理：
 * - 如果在250ms内再次触发resize，会清除之前的计时器重新计时
 * - 只有在最后一次resize后的250ms内没有新的resize事件，才会执行实际操作
 * - 这样可以大大减少函数执行次数，提升性能
 */
function handleWindowResize() {
    // 清除之前的计时器
    clearTimeout(resizeTimeout);

    // 设置新的计时器，延迟250ms执行
    resizeTimeout = setTimeout(() => {
        console.log('[响应式] 窗口大小已改变，调整图表尺寸...');

        // 获取所有Chart.js实例
        // Chart.instances 是Chart.js全局属性，存储所有创建的图表实例
        const charts = Chart.instances;

        // 遍历每个图表实例并调用resize方法
        charts.forEach(chart => {
            if (chart && typeof chart.resize === 'function') {
                chart.resize();
            }
        });

        // 触发自定义事件 'chartResize'
        // 其他组件可以监听此事件来执行自己的响应式逻辑
        window.dispatchEvent(new Event('chartResize'));

        console.log('[响应式] 图表尺寸调整完成');
    }, 250);  // 250毫秒延迟
}


// ==================== Bootstrap组件初始化模块 ====================

/**
 * 初始化所有Bootstrap工具提示（Tooltip）
 *
 * 功能说明：
 * - 工具提示是鼠标悬停在元素上时显示的小提示框
 * - 通过data-bs-toggle="tooltip"属性定义
 * - 可使用data-bs-title属性设置提示内容
 *
 * 使用示例：
 * <button data-bs-toggle="tooltip" data-bs-title="点击保存">保存</button>
 */
function initTooltips() {
    // 查找所有带有data-bs-toggle="tooltip"属性的元素
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');

    // 为每个元素创建Tooltip实例
    const tooltipList = [...tooltipTriggerList].map(
        tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl)
    );

    console.log(`[Bootstrap] 已初始化 ${tooltipList.length} 个工具提示`);
}

/**
 * 初始化所有Bootstrap弹出框（Popover）
 *
 * 功能说明：
 * - Popover是点击元素后显示的弹出式信息框
 * - 比Tooltip功能更强大，可以包含HTML内容、标题等
 * - 通过data-bs-toggle="popover"属性定义
 *
 * 使用示例：
 * <button data-bs-toggle="popover" data-bs-title="标题" data-bs-content="内容">点击查看</button>
 */
function initPopovers() {
    // 查找所有带有data-bs-toggle="popover"属性的元素
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');

    // 为每个元素创建Popover实例
    const popoverList = [...popoverTriggerList].map(
        popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl)
    );

    console.log(`[Bootstrap] 已初始化 ${popoverList.length} 个弹出框`);
}


// ==================== UI交互功能模块 ====================

/**
 * 初始化平滑滚动功能
 *
 * 功能说明：
 * - 为所有以#开头的锚点链接添加平滑滚动效果
 * - 点击链接时，页面会平滑滚动到目标位置，而不是瞬间跳转
 * - 提升用户体验，使页面导航更加自然流畅
 *
 * 实现原理：
 * - 监听所有a[href^="#"]元素的点击事件
 * - 使用scrollIntoView API实现平滑滚动
 * - block: 'start' 表示滚动到元素的顶部
 *
 * 注意事项：
 * - 排除href="#"的链接（空锚点）
 * - 需要CSS配合，html元素设置scroll-behavior: smooth
 */
function initSmoothScroll() {
    // 查找所有href属性以#开头的链接
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        // 为每个链接添加点击事件监听器
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');

            // 排除href="#"的情况（空锚点）
            if (href !== '#') {
                // 阻止默认的跳转行为
                e.preventDefault();

                // 查找目标元素
                const target = document.querySelector(href);

                if (target) {
                    // 平滑滚动到目标元素
                    // behavior: 'smooth' - 平滑滚动效果
                    // block: 'start' - 滚动到元素的顶部
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    console.log('[交互] 平滑滚动功能已启用');
}


// ==================== 表格功能模块 ====================

/**
 * 初始化表格排序功能
 *
 * 功能说明：
 * - 为所有带.table-sortable类的表格添加点击排序功能
 * - 用户点击表头时，该列会按升序或降序排列
 * - 支持数字排序和中文文本排序
 * - 支持切换排序方向（升序/降序）
 *
 * 使用方法：
 * - 给table元素添加class="table-sortable"
 * - 如果某列不需要排序，给th添加data-sortable="false"
 *
 * 示例：
 * <table class="table table-sortable">
 *   <thead>
 *     <tr>
 *       <th>名称</th>  <!-- 可排序 -->
 *       <th data-sortable="false">操作</th>  <!-- 不可排序 -->
 *     </tr>
 *   </thead>
 * </table>
 */
function initTableSorting() {
    // 查找所有带.table-sortable类的表格
    const tables = document.querySelectorAll('.table-sortable');

    tables.forEach(table => {
        // 获取表头元素
        const headers = table.querySelectorAll('th');

        // 为每个表头添加点击事件
        headers.forEach((header, index) => {
            // 检查该列是否允许排序
            // data-sortable="false" 表示不可排序
            if (header.dataset.sortable !== 'false') {
                // 设置鼠标样式为pointer，提示用户可点击
                header.style.cursor = 'pointer';

                // 添加点击事件监听器
                header.addEventListener('click', () => {
                    // 调用排序函数，传入表格和列索引
                    sortTable(table, index);
                });
            }
        });
    });

    console.log(`[表格] 已为 ${tables.length} 个表格添加排序功能`);
}

/**
 * 排序表格
 *
 * @param {HTMLTableElement} table - 要排序的表格元素
 * @param {number} columnIndex - 要排序的列索引（从0开始）
 *
 * 排序逻辑：
 * 1. 获取表格tbody中的所有行
 * 2. 根据表格当前的排序状态，判断是升序还是降序
 * 3. 对每一行的指定列进行比较和排序
 * 4. 支持数字排序和中文文本排序
 * 5. 重新排序表格的行
 * 6. 更新表格的排序状态标记
 */
function sortTable(table, columnIndex) {
    console.log(`[表格] 开始对第 ${columnIndex} 列进行排序...`);

    // 获取表格的tbody元素
    const tbody = table.querySelector('tbody');

    // 将tbody中的所有行转换为数组
    // 使用Array.from可以避免NodeList的限制
    const rows = Array.from(tbody.querySelectorAll('tr'));

    // 确定排序方向
    // 从table的data-sort-order属性中读取当前排序状态
    // 如果不是'asc'，则按升序排序；否则按降序排序
    const isAscending = table.dataset.sortOrder !== 'asc';

    // 对行数组进行排序
    rows.sort((a, b) => {
        // 获取两行中指定列的文本内容
        const aVal = a.cells[columnIndex].textContent.trim();
        const bVal = b.cells[columnIndex].textContent.trim();

        // 尝试将文本转换为数字进行数字排序
        const aNum = parseFloat(aVal);
        const bNum = parseFloat(bVal);

        // 如果两个值都是有效的数字，按数字排序
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? aNum - bNum : bNum - aNum;
        }

        // 如果不是数字，按字符串排序
        // 使用localeCompare支持中文排序
        return isAscending
            ? aVal.localeCompare(bVal, 'zh-CN')
            : bVal.localeCompare(aVal, 'zh-CN');
    });

    // 将排序后的行重新添加到tbody中
    // appendChild会将元素从原位置移除并添加到新位置
    rows.forEach(row => tbody.appendChild(row));

    // 更新表格的排序状态
    table.dataset.sortOrder = isAscending ? 'asc' : 'desc';

    console.log(`[表格] 排序完成，当前顺序: ${table.dataset.sortOrder}`);
}


// ==================== 搜索高亮功能模块 ====================

/**
 * 初始化搜索高亮功能
 *
 * 功能说明：
 * - 监听搜索输入框的输入事件
 * - 用户输入内容后，实时在表格中高亮匹配的文本
 * - 使用防抖技术，避免频繁更新DOM导致性能问题
 *
 * 实现原理：
 * 1. 查找页面的搜索输入框（name="search"）
 * 2. 监听input事件，每次输入时触发
 * 3. 使用300ms防抖延迟
 * 4. 调用highlightSearchResults函数执行高亮逻辑
 *
 * 注意事项：
 * - 需要页面上存在name="search"的input元素
 * - 需要页面上存在表格
 */
function initSearchHighlight() {
    // 查找搜索输入框
    const searchInput = document.querySelector('input[name="search"]');

    // 查找表格的tbody
    const tableBody = document.querySelector('.table tbody');

    // 如果搜索框和表格都存在，则初始化功能
    if (searchInput && tableBody) {
        let timeout;

        // 监听输入事件
        searchInput.addEventListener('input', function() {
            // 清除之前的计时器
            clearTimeout(timeout);

            // 设置300ms延迟后执行搜索
            // 避免用户快速输入时频繁触发
            timeout = setTimeout(() => {
                highlightSearchResults(this.value);
            }, 300);
        });

        console.log('[搜索] 搜索高亮功能已初始化');
    }
}

/**
 * 高亮搜索结果
 *
 * @param {string} searchTerm - 用户输入的搜索词
 *
 * 功能说明：
 * - 在表格的所有单元格中查找匹配的文本
 * - 使用<mark>标签包裹匹配的文本，实现黄色高亮效果
 * - 支持不区分大小写的搜索
 * - 每次搜索前先重置之前的高亮
 *
 * 实现原理：
 * 1. 获取表格所有单元格
 * 2. 重置单元格内容（移除之前的mark标签）
 * 3. 如果搜索词不为空，使用正则表达式查找匹配项
 * 4. 用<mark>标签替换匹配的文本
 * 5. 重新赋值给单元格的innerHTML
 *
 * 注意事项：
 * - 使用innerHTML会破坏原有的事件绑定，需要小心使用
 * - searchTerm需要进行正则转义，避免特殊字符导致错误
 */
function highlightSearchResults(searchTerm) {
    console.log(`[搜索] 高亮搜索词: "${searchTerm}"`);

    // 获取表格的所有单元格
    const tableCells = document.querySelectorAll('.table tbody td');

    // 遍历每个单元格
    tableCells.forEach(cell => {
        // 先重置单元格内容
        // textContent返回纯文本，可以去除之前的HTML标签
        cell.innerHTML = cell.textContent;

        // 如果搜索词不为空，执行高亮逻辑
        if (searchTerm.trim() !== '') {
            // 获取单元格的纯文本内容
            const text = cell.textContent;

            // 创建正则表达式
            // escapeRegExp用于转义特殊字符
            // 'gi' 标志：g-全局匹配，i-不区分大小写
            const regex = new RegExp(`(${escapeRegExp(searchTerm)})`, 'gi');

            // 使用<mark>标签替换匹配的文本
            // $1 表示正则表达式中第一个捕获组的内容
            cell.innerHTML = text.replace(regex, '<mark>$1</mark>');
        }
    });
}

/**
 * 转义正则表达式特殊字符
 *
 * @param {string} string - 要转义的字符串
 * @returns {string} - 转义后的字符串
 *
 * 功能说明：
 * - 将字符串中的正则表达式元字符转义为普通字符
 * - 避免在创建正则表达式时出现语法错误
 *
 * 需要转义的特殊字符：
 * - . * + ? ^ $ { } ( ) | [ ] \
 *
 * 使用场景：
 * - 当用户输入包含特殊字符的搜索词时
 * - 直接使用正则表达式会导致匹配失败或报错
 * - 转义后这些字符会被当作普通字符处理
 *
 * 示例：
 * - 输入: "test.com"
 * - 输出: "test\\.com"
 * - 这样正则表达式中的.就不会被当作通配符
 */
function escapeRegExp(string) {
    // 正则表达式匹配所有特殊字符
    // \\$& 表示在特殊字符前加反斜杠
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}


// ==================== 工具函数模块 ====================

/**
 * 格式化数字
 *
 * @param {number} num - 要格式化的数字
 * @param {number} decimals - 小数位数，默认为2
 * @returns {string} - 格式化后的字符串
 *
 * 功能说明：
 * - 将数字格式化为千分位分隔的形式
 * - 支持指定小数位数
 * - 使用中文本地化规则
 *
 * 示例：
 * - formatNumber(1234.567) => "1,234.57"
 * - formatNumber(1234567, 0) => "1,234,567"
 * - formatNumber(1000.5, 3) => "1,000.500"
 */
function formatNumber(num, decimals = 2) {
    return num.toLocaleString('zh-CN', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

/**
 * 格式化日期
 *
 * @param {Date|string} date - 日期对象或日期字符串
 * @param {string} format - 格式字符串，默认为'YYYY-MM-DD HH:mm:ss'
 * @returns {string} - 格式化后的日期字符串
 *
 * 支持的格式占位符：
 * - YYYY - 四位年份
 * - MM - 两位月份
 * - DD - 两位日期
 * - HH - 两位小时（24小时制）
 * - mm - 两位分钟
 * - ss - 两位秒
 *
 * 示例：
 * - formatDate(new Date()) => "2024-01-15 14:30:45"
 * - formatDate('2024-01-15', 'YYYY-MM-DD') => "2024-01-15"
 */
function formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
    // 如果传入的是字符串，转换为Date对象
    if (typeof date === 'string') {
        date = new Date(date);
    }

    // 获取日期的各个部分
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');

    // 使用replace替换格式字符串中的占位符
    return format
        .replace('YYYY', year)
        .replace('MM', month)
        .replace('DD', day)
        .replace('HH', hours)
        .replace('mm', minutes)
        .replace('ss', seconds);
}

/**
 * 显示加载动画
 *
 * @returns {HTMLDivElement} - 加载动画的DOM元素，用于后续移除
 *
 * 功能说明：
 * - 创建一个全屏的加载遮罩层
 * - 阻止用户在加载过程中进行操作
 * - 返回DOM元素，方便调用者后续移除
 *
 * 样式特点：
 * - position: fixed - 固定定位，覆盖整个视口
 * - 背景半透明白色：rgba(255, 255, 255, 0.8)
 * - z-index: 9999 - 确保在最上层显示
 * - Flex布局实现居中对齐
 *
 * 使用方法：
 * const loading = showLoading();
 * // ... 执行异步操作 ...
 * hideLoading(loading);
 */
function showLoading() {
    // 创建遮罩层div
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-overlay';
    loadingDiv.innerHTML = '<div class="loading"></div>';

    // 设置内联样式
    loadingDiv.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.8);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    `;

    // 添加到页面
    document.body.appendChild(loadingDiv);

    return loadingDiv;
}

/**
 * 隐藏加载动画
 *
 * @param {HTMLDivElement} loadingDiv - showLoading返回的DOM元素
 *
 * 功能说明：
 * - 从页面中移除加载遮罩层
 * - 恢复用户操作
 */
function hideLoading(loadingDiv) {
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

/**
 * AJAX请求封装函数
 *
 * @param {string} url - 请求的URL地址
 * @param {Object} options - fetch API的配置选项
 * @returns {Promise<Object>} - 返回JSON格式的响应数据
 *
 * 功能说明：
 * - 封装fetch API，提供统一的请求处理
 * - 自动显示和隐藏加载动画
 * - 自动处理错误
 * - 统一设置Content-Type为application/json
 *
 * 使用示例：
 * try {
 *     const data = await fetchData('/api/users', { method: 'POST' });
 *     console.log(data);
 * } catch (error) {
 *     console.error('请求失败', error);
 * }
 */
async function fetchData(url, options = {}) {
    // 显示加载动画
    const loading = showLoading();

    try {
        // 发送fetch请求
        const response = await fetch(url, {
            // 设置默认请求头
            headers: {
                'Content-Type': 'application/json',
                ...options.headers  // 允许覆盖默认headers
            },
            ...options  // 合并其他选项（method, body等）
        });

        // 检查响应状态
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // 返回JSON数据
        return await response.json();
    } catch (error) {
        // 错误处理
        console.error('Fetch error:', error);
        throw error;
    } finally {
        // 无论成功还是失败，都隐藏加载动画
        hideLoading(loading);
    }
}

/**
 * 显示Toast提示消息
 *
 * @param {string} message - 要显示的消息内容
 * @param {string} type - 消息类型，默认为'info'
 *                        可选值: 'success' | 'danger' | 'warning' | 'info'
 *
 * 功能说明：
 * - 在页面右上角显示一个自动消失的提示消息
 * - 使用Bootstrap的Toast组件
 * - 3秒后自动移除
 *
 * 消息类型：
 * - success - 成功（绿色）
 * - danger - 错误（红色）
 * - warning - 警告（黄色）
 * - info - 信息（蓝色）
 *
 * 使用示例：
 * showToast('操作成功', 'success');
 * showToast('发生错误', 'danger');
 */
function showToast(message, type = 'info') {
    // 获取或创建Toast容器
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();

    // 创建Toast元素
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 show`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    // 设置Toast的HTML内容
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    // 将Toast添加到容器
    toastContainer.appendChild(toast);

    // 3秒后自动移除
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

/**
 * 创建Toast容器
 *
 * @returns {HTMLDivElement} - Toast容器的DOM元素
 *
 * 功能说明：
 * - 创建一个固定在页面右上角的容器
 * - 用于存放所有的Toast提示消息
 * - 如果页面已存在容器，则复用现有容器
 *
 * 样式特点：
 * - position: fixed - 固定定位
 * - top-0 end-0 - 右上角
 * - z-index: 9999 - 确保在最上层
 */
function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

/**
 * 确认对话框
 *
 * @param {string} message - 要显示的确认消息
 * @param {Function} callback - 用户点击"确定"后执行的回调函数
 *
 * 功能说明：
 * - 显示浏览器的确认对话框
 * - 用户点击"确定"时执行回调函数
 * - 用户点击"取消"时不执行任何操作
 *
 * 使用示例：
 * confirmAction('确定要删除这条数据吗？', () => {
 *     // 删除操作
 *     deleteItem(id);
 * });
 */
function confirmAction(message, callback) {
    if (window.confirm(message)) {
        callback();
    }
}

/**
 * 复制文本到剪贴板
 *
 * @param {string} text - 要复制的文本内容
 *
 * 功能说明：
 * - 使用Clipboard API将文本复制到系统剪贴板
 * - 复制成功或失败时显示Toast提示
 *
 * 兼容性说明：
 * - 需要在HTTPS或localhost环境下使用
 * - 大部分现代浏览器都支持
 *
 * 使用示例：
 * copyToClipboard('https://example.com');
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('已复制到剪贴板', 'success');
    }).catch(err => {
        console.error('复制失败:', err);
        showToast('复制失败', 'danger');
    });
}

/**
 * 导出数据为CSV文件
 *
 * @param {Array<Object>} data - 要导出的数据数组，每个对象代表一行
 * @param {string} filename - 导出的文件名，默认为'export.csv'
 *
 * 功能说明：
 * - 将JSON格式的数据转换为CSV格式
 * - 自动触发浏览器下载
 * - CSV文件使用逗号分隔，适合在Excel中打开
 *
 * 使用示例：
 * const data = [
 *     { name: '张三', age: 25, city: '北京' },
 *     { name: '李四', age: 30, city: '上海' }
 * ];
 * exportToCSV(data, 'users.csv');
 */
function exportToCSV(data, filename = 'export.csv') {
    // 将数组转换为CSV格式字符串
    const csv = arrayToCSV(data);

    // 下载CSV文件
    downloadCSV(csv, filename);
}

/**
 * 将数组数据转换为CSV格式字符串
 *
 * @param {Array<Object>} data - 要转换的数据数组
 * @returns {string} - CSV格式的字符串
 *
 * 功能说明：
 * - 第一行是列名（对象的键）
 * - 后续每行是数据
 * - 使用逗号分隔字段
 * - 使用JSON.stringify处理字段值，确保特殊字符正确转义
 * - 空值转换为空字符串
 *
 * CSV格式示例：
 * name,age,city
 * "张三",25,"北京"
 * "李四",30,"上海"
 */
function arrayToCSV(data) {
    // 获取列名（对象的所有键）
    const headers = Object.keys(data[0]);

    // 将每行数据转换为CSV格式的字符串数组
    const rows = data.map(row =>
        headers.map(fieldName =>
            // 使用JSON.stringify处理字段值
            // 回调函数将null转为空字符串
            JSON.stringify(row[fieldName], (key, value) => value === null ? '' : value)
        )
    );

    // 合并表头和所有行
    // 使用join('\r\n')添加换行符
    return [headers.join(','), ...rows].join('\r\n');
}

/**
 * 下载CSV文件
 *
 * @param {string} csv - CSV格式的字符串
 * @param {string} filename - 要下载的文件名
 *
 * 功能说明：
 * - 创建一个临时的a标签
 * - 使用Blob对象创建CSV文件
 * - 触发浏览器的下载行为
 * - 下载完成后移除临时元素
 *
 * 实现原理：
 * 1. 创建Blob对象，类型为text/csv;charset=utf-8;
 * 2. 创建URL对象（使用URL.createObjectURL）
 * 3. 创建a标签并设置href和download属性
 * 4. 模拟点击触发下载
 * 5. 释放URL对象并移除a标签
 */
function downloadCSV(csv, filename) {
    // 创建Blob对象
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });

    // 创建URL对象
    const url = URL.createObjectURL(blob);

    // 创建a标签
    const link = document.createElement('a');

    // 设置下载属性
    link.setAttribute('href', url);
    link.setAttribute('download', filename);

    // 隐藏a标签
    link.style.visibility = 'hidden';

    // 添加到DOM
    document.body.appendChild(link);

    // 模拟点击
    link.click();

    // 移除a标签
    document.body.removeChild(link);

    // 释放URL对象
    URL.revokeObjectURL(url);
}

/**
 * 表单验证函数
 *
 * @param {HTMLFormElement} form - 要验证的表单元素
 * @returns {boolean} - 验证是否通过
 *
 * 功能说明：
 * - 检查所有必填字段（带required属性的input和select）
 * - 如果必填字段为空，添加is-invalid样式显示错误提示
 * - 如果必填字段有值，移除is-invalid样式
 * - 返回验证结果
 *
 * 使用方法：
 * <form id="myForm">
 *   <input type="text" required name="username">
 * </form>
 *
 * if (validateForm(document.getElementById('myForm'))) {
 *     // 表单验证通过，可以提交
 *     submitForm();
 * }
 */
function validateForm(form) {
    // 查找所有必填字段
    const inputs = form.querySelectorAll('input[required], select[required]');
    let isValid = true;

    // 遍历每个必填字段
    inputs.forEach(input => {
        // 检查字段值是否为空（trim去除首尾空格）
        if (!input.value.trim()) {
            // 添加错误样式
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            // 移除错误样式
            input.classList.remove('is-invalid');
        }
    });

    return isValid;
}
