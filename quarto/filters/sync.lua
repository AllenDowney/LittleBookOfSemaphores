-- Quarto / Pandoc filter: turn Divs with class "sync" into Sync embed mounts.
--
-- Authoring (HTML books only):
--
--   ::: {.sync example="mutex.py"}
--   :::
--
-- Emits a visible pending <pre> until sync_embed.js replaces it with a widget.
-- Attribute "file" is accepted as an alias for "example".

local function has_class(el, name)
  for _, cls in ipairs(el.classes) do
    if cls == name then
      return true
    end
  end
  return false
end

local function escape_html(s)
  return (s:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"):gsub('"', "&quot;"))
end

local function escape_attr(s)
  return escape_html(s):gsub("%s", " ")
end

function Div(el)
  if not FORMAT:match("html") then
    return nil
  end
  if not has_class(el, "sync") then
    return nil
  end

  local example = el.attributes["example"] or el.attributes["file"]
  if not example or example == "" then
    return pandoc.RawBlock(
      "html",
      '<div class="sync-embed sync-error"><p>Sync embed requires example="file.py"</p></div>'
    )
  end

  local label = escape_html(example)
  local attr = escape_attr(example)
  local html = string.format(
    '<div class="sync-embed sync-pending" data-example="%s">\n'
      .. '<pre class="sync-pending-code">Sync example: %s\n(loading interactive simulator…)</pre>\n'
      .. "</div>",
    attr,
    label
  )
  return pandoc.RawBlock("html", html)
end
