animebuffer.ready(function () {
  var terms = animebuffer.storage.get(
    'terms',
    ['quantum', 'WASM', 'physics','anime','о моем перерождении в слизь']
  );

  if (!Array.isArray(terms) || !terms.length) return;

  terms = terms
    .map(String)
    .filter(Boolean)
    .slice(0, 30);

  var escaped = terms.map(function (term) {
    return term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  });

  var re = new RegExp(
    '(' + escaped.join('|') + ')',
    'gi'
  );

  var walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT
  );

  var nodes = [];
  var node;

  while ((node = walker.nextNode())) {
    var parent = node.parentElement;

    if (!parent) continue;

    if (parent.closest('script,style,textarea,mark')) {
      continue;
    }

    nodes.push(node);
  }

  nodes.forEach(function (textNode) {
    var text = textNode.nodeValue;

    re.lastIndex = 0;

    if (!re.test(text)) return;

    re.lastIndex = 0;

    var fragment = document.createDocumentFragment();
    var position = 0;

    text.replace(re, function (match, unused, offset) {
      fragment.appendChild(
        document.createTextNode(
          text.slice(position, offset)
        )
      );

      var mark = document.createElement('mark');
      mark.textContent = match;
      mark.setAttribute('data-animebuffer-highlight', '1');
      fragment.appendChild(mark);

      position = offset + match.length;
    });

    fragment.appendChild(
      document.createTextNode(text.slice(position))
    );

    textNode.parentNode.replaceChild(
      fragment,
      textNode
    );
  });

  animebuffer.css(
    'mark[data-animebuffer-highlight] {' +
    'background: rgba(192,132,252,.42);' +
    'color: inherit;' +
    'border-radius: 3px;' +
    'padding: 0 2px;' +
    '}'
  );
});
