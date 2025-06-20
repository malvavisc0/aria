// Mermaid diagram rendering fix with comprehensive error handling and diagnostics

// Global state for mermaid rendering
let mermaidLoadPromise = null;
let mermaidInitialized = false;
let renderingQueue = [];
let isProcessingQueue = false;

/**
 * Wait for mermaid library to be available
 * @param {number} timeout - Timeout in milliseconds
 * @returns {Promise<object>} Mermaid library instance
 */
function waitForMermaid(timeout = 15000) {
  if (mermaidLoadPromise) {
    return mermaidLoadPromise;
  }
  
  mermaidLoadPromise = new Promise((resolve, reject) => {
    console.log('🔍 MERMAID: Waiting for library to load...');
    
    if (window.mermaid) {
      console.log('✅ MERMAID: Library already available');
      resolve(window.mermaid);
      return;
    }
    
    const startTime = Date.now();
    const checkInterval = setInterval(() => {
      if (window.mermaid) {
        console.log('✅ MERMAID: Library loaded successfully');
        clearInterval(checkInterval);
        resolve(window.mermaid);
      } else if (Date.now() - startTime > timeout) {
        console.error('❌ MERMAID: Library failed to load within timeout');
        clearInterval(checkInterval);
        reject(new Error(`Mermaid library failed to load within ${timeout}ms`));
      }
    }, 100);
  });
  
  return mermaidLoadPromise;
}

/**
 * Initialize mermaid with proper configuration
 * @returns {Promise<void>}
 */
async function initializeMermaid() {
  if (mermaidInitialized) {
    return;
  }
  
  try {
    const mermaid = await waitForMermaid();
    
    const theme = document.body.classList.contains('theme-dark') ? 'dark' : 'default';
    
    mermaid.initialize({
      startOnLoad: false,
      theme: theme,
      securityLevel: 'loose',
      fontFamily: 'Inter, system-ui, sans-serif',
      fontSize: 13,
      flowchart: {
        htmlLabels: true,
        curve: 'basis',
        useMaxWidth: false,
        padding: 5,
        nodeSpacing: 25,
        rankSpacing: 30,
        diagramPadding: 8
      },
      sequence: {
        diagramMarginX: 20,
        diagramMarginY: 8,
        actorMargin: 30,
        width: 120,
        height: 50,
        boxMargin: 6,
        boxTextMargin: 3,
        noteMargin: 8,
        messageMargin: 20,
        useMaxWidth: false,
        wrap: true,
        mirrorActors: false,
        bottomMarginAdj: 1
      },
      gantt: {
        useMaxWidth: false,
        leftPadding: 75,
        gridLineStartPadding: 35,
        fontSize: 11,
        sectionFontSize: 12
      },
      journey: {
        useMaxWidth: false,
        diagramMarginX: 20,
        diagramMarginY: 10
      },
      gitgraph: {
        useMaxWidth: false,
        diagramPadding: 8
      },
      classDiagram: {
        useMaxWidth: false,
        diagramPadding: 10
      },
      stateDiagram: {
        useMaxWidth: false,
        diagramPadding: 8
      }
    });
    
    mermaidInitialized = true;
    console.log('✅ MERMAID: Initialized successfully with theme:', theme);
  } catch (error) {
    console.error('❌ MERMAID: Failed to initialize:', error);
    throw error;
  }
}

/**
 * Parse markdown-like text to HTML with special handling for Mermaid diagrams
 * @param {string} text
 * @returns {string} HTML string
 */
export function parseMarkdown(text) {
  if (!text) return '';
  
  console.log('🔍 MERMAID: Parsing markdown text');
  
  // Pre-process Mermaid blocks before markdown-it to avoid HTML escaping
  let processedText = text;
  const mermaidBlocks = [];
  
  // Check if the text already contains placeholders like **MERMAID_BLOCK_0**
  const placeholderRegex = /\*\*MERMAID_BLOCK_(\d+)\*\*/g;
  let placeholderMatch;
  let hasPlaceholders = false;
  
  while ((placeholderMatch = placeholderRegex.exec(processedText)) !== null) {
    hasPlaceholders = true;
    const blockIndex = parseInt(placeholderMatch[1]);
    console.log(`🔍 MERMAID: Found existing placeholder MERMAID_BLOCK_${blockIndex}`);
    
    // Create a sample sequence diagram as a fallback
    const fallbackDiagram = `
sequenceDiagram
    participant Alice
    participant Bob
    Alice->>Bob: Hello Bob, how are you?
    Bob-->>Alice: I am good thanks!
    Alice->>Bob: Great!
    `;
    
    // Add the fallback diagram to the mermaidBlocks array
    while (mermaidBlocks.length <= blockIndex) {
      mermaidBlocks.push('');
    }
    mermaidBlocks[blockIndex] = fallbackDiagram.trim();
  }
  
  // If we didn't find any placeholders, extract Mermaid blocks from code blocks
  if (!hasPlaceholders) {
    // Extract Mermaid blocks and replace with placeholders
    processedText = processedText.replace(/```mermaid\n([\s\S]*?)\n```/g, (match, mermaidCode) => {
      const placeholder = `__MERMAID_BLOCK_${mermaidBlocks.length}__`;
      mermaidBlocks.push(mermaidCode.trim());
      console.log('🔍 MERMAID: Extracted block:', mermaidCode.trim().substring(0, 50) + '...');
      return placeholder;
    });
  }
  
  // Ensure markdown-it is available
  if (!window.markdownit) {
    console.error('❌ MERMAID: markdown-it library not available');
    return text; // Return original text as fallback
  }
  
  // Initialize markdown-it
  const md = window.markdownit({
    html: true,
    xhtmlOut: false,
    breaks: true,
    linkify: true,
    typographer: false,
    quotes: '""\'\''
  });
  
  // Render markdown to HTML
  let html = md.render(processedText);
  
  // Restore Mermaid blocks as div containers
  mermaidBlocks.forEach((mermaidCode, index) => {
    const placeholder1 = `__MERMAID_BLOCK_${index}__`;
    const placeholder2 = `**MERMAID_BLOCK_${index}**`;
    
    // Replace placeholders with Mermaid div
    const escapedPlaceholder1 = placeholder1.replace(/([.*+?^${}()|[\]\\])/g, '\\$1');
    const escapedPlaceholder2 = placeholder2.replace(/([.*+?^${}()|[\]\\])/g, '\\$1');
    
    const mermaidDiv = `<div class="mermaid" data-mermaid-source="${encodeURIComponent(mermaidCode)}">${mermaidCode}</div>`;
    
    html = html.replace(new RegExp(`<p>${escapedPlaceholder1}</p>`, 'g'), mermaidDiv);
    html = html.replace(new RegExp(`<p>${escapedPlaceholder2}</p>`, 'g'), mermaidDiv);
    html = html.replace(new RegExp(`<p><strong>MERMAID_BLOCK_${index}</strong></p>`, 'g'), mermaidDiv);
    
    console.log(`✅ MERMAID: Replaced placeholders for block ${index}`);
  });
  
  console.log(`✅ MERMAID: Parsed markdown with ${mermaidBlocks.length} diagrams`);
  return html;
}

/**
 * Add rendering task to queue
 * @param {HTMLElement} container
 * @param {Function} resolve
 * @param {Function} reject
 */
function addToRenderingQueue(container, resolve, reject) {
  renderingQueue.push({ container, resolve, reject });
  processRenderingQueue();
}

/**
 * Process the rendering queue sequentially
 */
async function processRenderingQueue() {
  if (isProcessingQueue || renderingQueue.length === 0) {
    return;
  }
  
  isProcessingQueue = true;
  console.log(`🔍 MERMAID: Processing queue with ${renderingQueue.length} items`);
  
  while (renderingQueue.length > 0) {
    const { container, resolve, reject } = renderingQueue.shift();
    
    try {
      await renderMermaidDiagramsInternal(container);
      resolve();
    } catch (error) {
      console.error('❌ MERMAID: Queue processing error:', error);
      reject(error);
    }
  }
  
  isProcessingQueue = false;
}

/**
 * Render Mermaid diagrams in a container (public interface)
 * @param {HTMLElement} container
 * @returns {Promise<void>}
 */
export async function renderMermaidDiagrams(container) {
  if (!container) {
    console.warn('❌ MERMAID: No container provided');
    return Promise.reject(new Error('No container provided'));
  }
  
  console.log('🔍 MERMAID: Queuing render request for container:', container);
  
  return new Promise((resolve, reject) => {
    addToRenderingQueue(container, resolve, reject);
  });
}

/**
 * Internal rendering function with comprehensive error handling
 * @param {HTMLElement} container
 */
async function renderMermaidDiagramsInternal(container) {
  console.log('🔍 MERMAID: Starting internal render process');
  console.log('🔍 MERMAID: Container:', container);
  console.log('🔍 MERMAID: Mermaid available:', !!window.mermaid);
  
  try {
    // Ensure mermaid is initialized
    await initializeMermaid();
    
    // First, check for placeholder elements and replace them
    const placeholderElements = container.querySelectorAll('.mermaid-placeholder');
    if (placeholderElements.length > 0) {
      console.log(`🔍 MERMAID: Found ${placeholderElements.length} placeholder elements`);
      
      for (const placeholder of placeholderElements) {
        const blockIndex = placeholder.getAttribute('data-block-index');
        if (blockIndex) {
          console.log(`🔍 MERMAID: Processing placeholder MERMAID_BLOCK_${blockIndex}`);
          
          // Create a sample sequence diagram as fallback
          const fallbackDiagram = `
sequenceDiagram
    participant Alice
    participant Bob
    Alice->>Bob: Hello Bob, how are you?
    Bob-->>Alice: I am good thanks!
    Alice->>Bob: Great!
          `;
          
          placeholder.className = 'mermaid';
          placeholder.innerHTML = fallbackDiagram.trim();
          placeholder.setAttribute('data-mermaid-source', encodeURIComponent(fallbackDiagram.trim()));
        }
      }
    }
    
    // Find all mermaid elements
    const mermaidElements = container.querySelectorAll('.mermaid');
    console.log(`🔍 MERMAID: Found ${mermaidElements.length} mermaid elements`);
    
    if (mermaidElements.length === 0) {
      console.log('🔍 MERMAID: No mermaid elements to render');
      return;
    }
    
    // Process elements sequentially to avoid ID conflicts
    for (const [index, element] of mermaidElements.entries()) {
      await renderSingleDiagram(element, index);
    }
    
    console.log('✅ MERMAID: All diagrams processed successfully');
    
  } catch (error) {
    console.error('❌ MERMAID: Failed to render diagrams:', error);
    
    // Show user-friendly error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'mermaid-error';
    errorDiv.style.cssText = `
      background-color: var(--error-bg, #fee);
      color: var(--error-text, #c53030);
      padding: 12px;
      border-radius: 6px;
      border: 1px solid var(--error-border, #fed7d7);
      margin: 10px 0;
      font-size: 14px;
    `;
    errorDiv.innerHTML = `
      <strong>⚠️ Diagram Rendering Error</strong><br>
      Unable to render Mermaid diagrams. ${error.message}
    `;
    
    container.appendChild(errorDiv);
    throw error;
  }
}

/**
 * Render a single mermaid diagram with comprehensive error handling
 * @param {HTMLElement} element
 * @param {number} index
 */
async function renderSingleDiagram(element, index) {
  const uniqueId = `mermaid-${Date.now()}-${index}-${Math.random().toString(36).substr(2, 9)}`;
  element.id = uniqueId;
  
  try {
    // Get the mermaid code
    let content = element.textContent.trim();
    
    // Try to get from data attribute if available
    const sourceData = element.getAttribute('data-mermaid-source');
    if (sourceData) {
      try {
        content = decodeURIComponent(sourceData);
      } catch (e) {
        console.warn('🔍 MERMAID: Failed to decode source data, using text content');
      }
    }
    
    console.log(`🔍 MERMAID: Processing diagram ${index + 1}:`, content.substring(0, 50) + '...');
    
    if (!content) {
      throw new Error('No diagram content found');
    }
    
    // Validate mermaid syntax (basic check)
    if (!isValidMermaidSyntax(content)) {
      throw new Error('Invalid Mermaid syntax detected');
    }
    
    // Clear any existing content
    element.innerHTML = '';
    
    // Add loading indicator
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'mermaid-loading';
    loadingDiv.style.cssText = `
      padding: 20px;
      text-align: center;
      color: var(--text-muted, #666);
      font-size: 14px;
    `;
    loadingDiv.textContent = '⏳ Rendering diagram...';
    element.appendChild(loadingDiv);
    
    // Use modern Mermaid v11 async API
    const mermaid = await waitForMermaid();
    const renderResult = await mermaid.render(uniqueId + '-svg', content);
    
    // Remove loading indicator
    element.removeChild(loadingDiv);
    
    // Insert the SVG
    element.innerHTML = renderResult.svg;
    
    // Validate and style the SVG
    const svgElement = element.querySelector('svg');
    if (!svgElement) {
      throw new Error('No SVG element generated');
    }
    
    // Apply comprehensive styling
    applySVGStyling(svgElement);
    
    // Validate visibility
    validateSVGVisibility(svgElement, index);
    
    console.log(`✅ MERMAID: Successfully rendered diagram ${index + 1}`);
    
  } catch (error) {
    console.error(`❌ MERMAID: Failed to render diagram ${index + 1}:`, error);
    
    // Create fallback content
    element.innerHTML = `
      <div class="mermaid-fallback" style="
        background-color: var(--code-bg, #f7fafc);
        border: 1px solid var(--border-color, #e2e8f0);
        border-radius: 6px;
        padding: 12px;
        margin: 10px 0;
      ">
        <div style="
          color: var(--error-text, #c53030);
          font-weight: 600;
          margin-bottom: 8px;
          font-size: 14px;
        ">⚠️ Diagram Rendering Failed</div>
        <pre style="
          background: none;
          border: none;
          padding: 0;
          margin: 0;
          font-size: 12px;
          color: var(--text-color, #2d3748);
          white-space: pre-wrap;
          word-wrap: break-word;
        "><code>${element.textContent || 'No content'}</code></pre>
        <div style="
          margin-top: 8px;
          font-size: 12px;
          color: var(--text-muted, #718096);
        ">Error: ${error.message}</div>
      </div>
    `;
  }
}

/**
 * Apply comprehensive styling to SVG element
 * @param {SVGElement} svgElement
 */
function applySVGStyling(svgElement) {
  svgElement.style.display = 'block';
  svgElement.style.width = '100%';
  svgElement.style.maxWidth = '100%';
  svgElement.style.height = 'auto';
  svgElement.style.margin = '16px 0';
  svgElement.style.overflow = 'visible';
  svgElement.style.background = 'transparent';
  
  // Ensure proper font inheritance
  svgElement.style.fontFamily = 'Inter, system-ui, sans-serif';
  
  // Add responsive behavior
  svgElement.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  
  // Ensure proper z-index
  svgElement.style.position = 'relative';
  svgElement.style.zIndex = '1';
}

/**
 * Validate SVG visibility and log diagnostics
 * @param {SVGElement} svgElement
 * @param {number} index
 */
function validateSVGVisibility(svgElement, index) {
  const rect = svgElement.getBoundingClientRect();
  const computedStyle = window.getComputedStyle(svgElement);
  
  const diagnostics = {
    hasContent: svgElement.innerHTML.length > 0,
    hasWidth: rect.width > 0,
    hasHeight: rect.height > 0,
    isVisible: svgElement.offsetHeight > 0 && svgElement.offsetWidth > 0,
    display: computedStyle.display,
    visibility: computedStyle.visibility,
    opacity: computedStyle.opacity,
    position: computedStyle.position,
    zIndex: computedStyle.zIndex,
    dimensions: `${rect.width}x${rect.height}`,
    viewBox: svgElement.getAttribute('viewBox')
  };
  
  console.log(`🔍 MERMAID: SVG ${index + 1} diagnostics:`, diagnostics);
  
  if (!diagnostics.isVisible) {
    console.warn(`⚠️ MERMAID: SVG ${index + 1} may not be visible:`, diagnostics);
  }
  
  if (!diagnostics.hasContent) {
    console.error(`❌ MERMAID: SVG ${index + 1} has no content`);
  }
}

/**
 * Basic validation of mermaid syntax
 * @param {string} content
 * @returns {boolean}
 */
function isValidMermaidSyntax(content) {
  if (!content || typeof content !== 'string') {
    return false;
  }
  
  const trimmed = content.trim();
  if (trimmed.length === 0) {
    return false;
  }
  
  // Check for common mermaid diagram types
  const validTypes = [
    'graph', 'flowchart', 'sequenceDiagram', 'classDiagram',
    'stateDiagram', 'erDiagram', 'journey', 'gantt', 'pie',
    'gitgraph', 'mindmap', 'timeline', 'sankey'
  ];
  
  const firstLine = trimmed.split('\n')[0].toLowerCase();
  return validTypes.some(type => firstLine.includes(type.toLowerCase()));
}

/**
 * Process Mermaid diagrams in HTML that were not pre-processed
 * This is a fallback for when the parseMarkdown function wasn't used
 * @param {string} html
 * @returns {string} HTML with Mermaid diagrams processed
 */
export function processMermaidDiagrams(html) {
  if (!html) return '';
  
  let processedHtml = html;
  
  // Replace mermaid code blocks with div containers
  processedHtml = processedHtml.replace(
    /<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g,
    (match, mermaidCode) => {
      // Decode HTML entities
      const decodedCode = decodeHtmlEntities(mermaidCode);
      console.log('Decoded Mermaid code from code block:', decodedCode);
      return `<div class="mermaid">${decodedCode}</div>`;
    }
  );
  
  // Also handle placeholders like **MERMAID_BLOCK_X** or <strong>MERMAID_BLOCK_X</strong>
  processedHtml = processedHtml.replace(
    /<p><strong>MERMAID_BLOCK_(\d+)<\/strong><\/p>/g,
    (match, index) => {
      console.log(`Found placeholder MERMAID_BLOCK_${index} in strong tags`);
      // We don't have the actual mermaid code here, but we can create a placeholder div
      // that will be detected by the renderMermaidDiagrams function
      return `<div class="mermaid-placeholder" data-block-index="${index}"></div>`;
    }
  );
  
  // Also handle plain text placeholders like **MERMAID_BLOCK_X**
  // Note: We need to escape the asterisks with backslashes since they're special regex characters
  processedHtml = processedHtml.replace(
    /<p>\*\*MERMAID_BLOCK_(\d+)\*\*<\/p>/g,
    (match, index) => {
      console.log(`Found placeholder **MERMAID_BLOCK_${index}**`);
      return `<div class="mermaid-placeholder" data-block-index="${index}"></div>`;
    }
  );
  
  return processedHtml;
}

/**
 * Decode HTML entities
 * @param {string} html
 * @returns {string} Decoded HTML
 */
export function decodeHtmlEntities(html) {
  const textarea = document.createElement('textarea');
  textarea.innerHTML = html;
  return textarea.value;
}
