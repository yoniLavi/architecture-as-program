-- Pandoc Lua filter for clean markdown export.
--
-- 1. Converts the centered title span into proper markdown structure
-- 2. Adds automatic section numbering to headings (1., 1.1, etc.)
-- 3. Resolves @sec:label cross-references to actual section numbers
-- 4. Adds --- separators between top-level sections

local counters = {}
local function reset_below(level)
  for i = level + 1, 6 do counters[i] = 0 end
end

local function next_number(level)
  counters[level] = (counters[level] or 0) + 1
  reset_below(level)
  local parts = {}
  for i = 1, level do
    parts[#parts + 1] = tostring(counters[i] or 0)
  end
  return table.concat(parts, ".")
end

function Pandoc(doc)
  -- Pass 1: walk headings to build label → section number map
  local label_map = {}
  local c = {}
  local numbering = true
  for _, block in ipairs(doc.blocks) do
    if block.t == "Header" then
      local text = pandoc.utils.stringify(block)
      if text:match("^Technical Note") or text:match("^Annex") then
        numbering = false
      end
      if numbering then
        local level = block.level
        c[level] = (c[level] or 0) + 1
        for i = level + 1, 6 do c[i] = 0 end
        local parts = {}
        for i = 1, level do parts[#parts + 1] = tostring(c[i] or 0) end
        local num = table.concat(parts, ".")
        local id = block.attr.identifier or ""
        if id ~= "" then
          label_map[id] = num
        end
      end
    end
  end

  -- Pass 2: transform blocks
  local numbering_enabled = true
  local new_blocks = pandoc.List()

  -- Helper: replace cross-references in an inline list using label_map
  local function resolve_crossrefs(inlines)
    local result = pandoc.List()
    local i = 1
    while i <= #inlines do
      local el = inlines[i]
      if el.t == "Cite"
        and #el.citations == 1
        and el.citations[1].id == "sec"
        and i + 1 <= #inlines
        and inlines[i + 1].t == "Str"
        and inlines[i + 1].text:match("^:")
      then
        local raw = inlines[i + 1].text:sub(2) -- strip leading ":"
        -- Separate label from trailing punctuation (e.g. "workflow:" → "workflow", ":")
        local label_suffix, trailing = raw:match("^([%w%-]+)(.*)")
        label_suffix = label_suffix or raw
        trailing = trailing or ""
        local full_label = "sec:" .. label_suffix
        local num = label_map[full_label]
        if num then
          result:insert(pandoc.Str("§" .. num .. trailing))
        else
          result:insert(pandoc.Str("§" .. label_suffix .. trailing))
        end
        i = i + 2
      else
        result:insert(el)
        i = i + 1
      end
    end
    return result
  end

  -- Helper: walk a block and resolve cross-references in all inlines
  local function resolve_block(block)
    return pandoc.walk_block(block, {
      Inlines = function(inlines) return resolve_crossrefs(inlines) end
    })
  end

  -- Track whether we've seen the title yet
  local title_emitted = false

  for _, block in ipairs(doc.blocks) do
    -- Convert centered spans in the title block
    if block.t == "Para" and #block.content >= 1 and block.content[1].t == "Span" then
      local span = block.content[1]
      local attrs = span.attributes or {}
      if attrs.align == "center" then
        -- Collect meaningful inlines (skip SoftBreak padding)
        local inlines = pandoc.List()
        for _, inline in ipairs(span.content) do
          if inline.t ~= "SoftBreak" then
            inlines:insert(inline)
          end
        end
        -- First centered block with Strong = title → H1
        if not title_emitted then
          for _, inline in ipairs(inlines) do
            if inline.t == "Strong" then
              new_blocks:insert(pandoc.Header(1, inline.content))
              title_emitted = true
              break
            end
          end
        else
          -- Subsequent centered blocks (authors, date) → bold paragraphs
          new_blocks:insert(pandoc.Para({pandoc.Strong(inlines)}))
        end
        goto continue
      end
    end

    -- Convert centered Div (e.g. author grid) to plain bold paragraphs
    if block.t == "Div" then
      local attrs = block.attributes or {}
      if attrs.align == "center" then
        for _, child in ipairs(block.content) do
          if child.t == "Table" then
            local lines = pandoc.List()
            -- Iterate table bodies → rows → cells
            for _, tbody in ipairs(child.bodies) do
              for _, row in ipairs(tbody.body) do
                local cells = {}
                for _, cell in ipairs(row.cells) do
                  cells[#cells + 1] = pandoc.utils.stringify(cell)
                end
                if #lines > 0 then lines:insert(pandoc.LineBreak()) end
                lines:insert(pandoc.Str(table.concat(cells, "  ·  ")))
              end
            end
            if #lines > 0 then
              new_blocks:insert(pandoc.Para({pandoc.Strong(lines)}))
            end
          end
        end
        goto continue
      end
    end

    -- Handle headings: number them and shift to H2/H3
    if block.t == "Header" then
      local level = block.level
      local text = pandoc.utils.stringify(block)
      if text:match("^Technical Note") or text:match("^Annex") then
        numbering_enabled = false
      end

      if numbering_enabled then
        if level == 1 and (counters[1] or 0) > 0 then
          new_blocks:insert(pandoc.HorizontalRule())
        end
        local num = next_number(level)
        local new_content = pandoc.List()
        new_content:insert(pandoc.Str(num .. "."))
        new_content:insert(pandoc.Space())
        new_content:extend(block.content)
        new_blocks:insert(pandoc.Header(level + 1, new_content, block.attr))
      else
        if level == 1 then
          new_blocks:insert(pandoc.HorizontalRule())
          new_blocks:insert(pandoc.Header(2, block.content, block.attr))
        else
          new_blocks:insert(pandoc.Header(level + 1, block.content, block.attr))
        end
      end
      goto continue
    end

    -- All other blocks: resolve cross-references in their inlines
    new_blocks:insert(resolve_block(block))
    ::continue::
  end

  doc.blocks = new_blocks
  return doc
end
