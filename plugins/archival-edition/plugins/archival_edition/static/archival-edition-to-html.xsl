<?xml version="1.0" encoding="UTF-8"?>
<!--
  Reading view of an archival edition document: a short summary of the header, then the
  transcription split into one box per page. A page runs from a <pb/> to the next one, so
  elements that cross a page break (a paragraph continued on the next page) appear in both boxes.

  XSLT 1.0, run in the browser by the editor's XSL viewer. No layout fidelity: line breaks are
  kept, editorial markup is shown inline with simple conventions ([…] for gaps, [text] for
  supplied text, struck-through deletions, underlined additions).
-->
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:tei="http://www.tei-c.org/ns/1.0"
  exclude-result-prefixes="tei">

  <xsl:output method="html" encoding="UTF-8" indent="no"/>

  <!-- page breaks of the transcription, in document order -->
  <xsl:variable name="pbs" select="/tei:TEI/tei:text//tei:pb"/>

  <xsl:template match="/">
    <html>
      <head>
        <title>
          <xsl:value-of select="normalize-space(/tei:TEI/tei:teiHeader/tei:fileDesc/tei:titleStmt/tei:title[1])"/>
        </title>
      </head>
      <body>
        <div class="ae-view">
          <style>
            .ae-view { font-family: Georgia, 'Times New Roman', serif; line-height: 1.5; color: #222; background: #f4f4f4; max-width: 48em; margin: 0 auto; padding: 1em; }
            .ae-view .ae-summary { margin-bottom: 1.5em; }
            .ae-view .ae-summary h2 { font-size: 1.3em; margin: 0 0 .3em; }
            .ae-view .ae-summary dl { display: grid; grid-template-columns: max-content 1fr; gap: .1em 1em; margin: .5em 0; font-size: .9em; }
            .ae-view .ae-summary dt { color: #666; }
            .ae-view .ae-summary dd { margin: 0; }
            .ae-view .ae-page { background: #fff; border: 1px solid #ccc; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,.12); padding: 1em 1.5em 1.5em; margin: 0 0 1.5em; }
            .ae-view .ae-page-label { font-family: sans-serif; font-size: .8em; color: #888; border-bottom: 1px solid #eee; margin: 0 0 .8em; padding-bottom: .3em; }
            .ae-view .ae-page p { margin: 0 0 .8em; }
            .ae-view .ae-block { margin: 0 0 .5em; }
            .ae-view .ae-right { text-align: right; }
            .ae-view .ae-fw { font-family: sans-serif; font-size: .8em; color: #888; }
            .ae-view .ae-unclear { border-bottom: 1px dotted #999; }
            .ae-view .ae-unclear::after { content: '(?)'; font-size: .75em; color: #999; }
            .ae-view .ae-gap, .ae-view .ae-supplied, .ae-view .ae-figure, .ae-view .ae-damage { color: #777; }
            .ae-view del { color: #888; }
            .ae-view ins { text-decoration: underline; }
            .ae-view .ae-alt { border-bottom: 1px dashed #999; cursor: help; }
            .ae-view .ae-note { font-size: .85em; color: #555; }
            .ae-view table { border-collapse: collapse; }
            .ae-view td { border: 1px solid #ccc; padding: .2em .5em; vertical-align: top; }
          </style>
          <xsl:apply-templates select="/tei:TEI/tei:teiHeader" mode="summary"/>
          <xsl:call-template name="pages"/>
        </div>
      </body>
    </html>
  </xsl:template>

  <!-- ===================== header summary ===================== -->

  <xsl:template match="tei:teiHeader" mode="summary">
    <xsl:variable name="ms" select="tei:fileDesc/tei:sourceDesc/tei:msDesc"/>
    <div class="ae-summary">
      <h2><xsl:value-of select="normalize-space(tei:fileDesc/tei:titleStmt/tei:title[1])"/></h2>
      <dl>
        <xsl:call-template name="summary-row">
          <xsl:with-param name="label">Date</xsl:with-param>
          <xsl:with-param name="value" select="$ms/tei:history/tei:origin/tei:origDate"/>
        </xsl:call-template>
        <xsl:call-template name="summary-row">
          <xsl:with-param name="label">Place</xsl:with-param>
          <xsl:with-param name="value" select="$ms/tei:history/tei:origin/tei:origPlace"/>
        </xsl:call-template>
        <xsl:if test="$ms/tei:msIdentifier">
          <dt>Source</dt>
          <dd>
            <xsl:for-each select="$ms/tei:msIdentifier/*[normalize-space()]">
              <xsl:if test="position() &gt; 1">, </xsl:if>
              <xsl:value-of select="normalize-space()"/>
            </xsl:for-each>
          </dd>
        </xsl:if>
        <xsl:call-template name="summary-row">
          <xsl:with-param name="label">Summary</xsl:with-param>
          <xsl:with-param name="value" select="tei:profileDesc/tei:abstract"/>
        </xsl:call-template>
      </dl>
    </div>
  </xsl:template>

  <xsl:template name="summary-row">
    <xsl:param name="label"/>
    <xsl:param name="value"/>
    <xsl:if test="normalize-space($value)">
      <dt><xsl:value-of select="$label"/></dt>
      <dd><xsl:value-of select="normalize-space($value)"/></dd>
    </xsl:if>
  </xsl:template>

  <!-- ===================== page boxes ===================== -->

  <!--
    Page k consists of the nodes whose nearest preceding <pb/> is the k-th one. Content before the
    first <pb/> (or the whole text, if there is none) gets a box of its own, identified by the
    empty id.
  -->
  <xsl:template name="pages">
    <xsl:variable name="text" select="/tei:TEI/tei:text"/>
    <xsl:if test="not($pbs) or $text//text()[normalize-space()][not(preceding::tei:pb)]">
      <xsl:call-template name="page">
        <xsl:with-param name="pb-id" select="''"/>
        <xsl:with-param name="label">
          <xsl:choose>
            <xsl:when test="$pbs">Before the first page break</xsl:when>
            <xsl:otherwise>Text</xsl:otherwise>
          </xsl:choose>
        </xsl:with-param>
      </xsl:call-template>
    </xsl:if>
    <xsl:for-each select="$pbs">
      <xsl:call-template name="page">
        <xsl:with-param name="pb-id" select="generate-id()"/>
        <xsl:with-param name="label">
          <xsl:text>Page </xsl:text>
          <xsl:choose>
            <xsl:when test="normalize-space(@n)"><xsl:value-of select="@n"/></xsl:when>
            <xsl:otherwise><xsl:value-of select="position()"/></xsl:otherwise>
          </xsl:choose>
        </xsl:with-param>
      </xsl:call-template>
    </xsl:for-each>
  </xsl:template>

  <xsl:template name="page">
    <xsl:param name="pb-id"/>
    <xsl:param name="label"/>
    <section class="ae-page">
      <div class="ae-page-label"><xsl:value-of select="$label"/></div>
      <xsl:apply-templates select="/tei:TEI/tei:text/*" mode="page">
        <xsl:with-param name="pb-id" select="$pb-id"/>
      </xsl:apply-templates>
    </section>
  </xsl:template>

  <!--
    Every template of mode "page" passes on only the children that belong to the page: nodes that
    start on it, and elements that contain its <pb/> (they started on an earlier page and continue).
  -->
  <xsl:template name="children">
    <xsl:param name="pb-id"/>
    <xsl:apply-templates mode="page"
      select="node()[generate-id(preceding::tei:pb[1]) = $pb-id or descendant::tei:pb[generate-id() = $pb-id]]">
      <xsl:with-param name="pb-id" select="$pb-id"/>
    </xsl:apply-templates>
  </xsl:template>

  <!-- elements without a rule of their own are transparent -->
  <xsl:template match="*" mode="page">
    <xsl:param name="pb-id"/>
    <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
  </xsl:template>

  <xsl:template match="text()" mode="page">
    <xsl:value-of select="."/>
  </xsl:template>

  <!-- not part of the reading text -->
  <xsl:template match="tei:pb | tei:cb | tei:milestone | tei:metamark | tei:graphic | tei:figDesc" mode="page"/>

  <!-- block elements -->
  <xsl:template match="tei:div | tei:front | tei:body | tei:back | tei:opener | tei:closer | tei:postscript | tei:address" mode="page">
    <xsl:param name="pb-id"/>
    <div class="ae-block ae-{local-name()}">
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </div>
  </xsl:template>

  <xsl:template match="tei:p | tei:ab" mode="page">
    <xsl:param name="pb-id"/>
    <p>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </p>
  </xsl:template>

  <xsl:template match="tei:head" mode="page">
    <xsl:param name="pb-id"/>
    <h3>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </h3>
  </xsl:template>

  <xsl:template match="tei:dateline | tei:salute | tei:signed | tei:addrLine" mode="page">
    <xsl:param name="pb-id"/>
    <div>
      <xsl:attribute name="class">
        <xsl:text>ae-block</xsl:text>
        <xsl:if test="self::tei:dateline or (self::tei:signed and parent::tei:closer)"> ae-right</xsl:if>
      </xsl:attribute>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </div>
  </xsl:template>

  <xsl:template match="tei:fw" mode="page">
    <xsl:param name="pb-id"/>
    <div class="ae-fw">
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </div>
  </xsl:template>

  <xsl:template match="tei:list" mode="page">
    <xsl:param name="pb-id"/>
    <ul>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </ul>
  </xsl:template>

  <xsl:template match="tei:item" mode="page">
    <xsl:param name="pb-id"/>
    <li>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </li>
  </xsl:template>

  <xsl:template match="tei:table" mode="page">
    <xsl:param name="pb-id"/>
    <table>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </table>
  </xsl:template>

  <xsl:template match="tei:row" mode="page">
    <xsl:param name="pb-id"/>
    <tr>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </tr>
  </xsl:template>

  <xsl:template match="tei:cell" mode="page">
    <xsl:param name="pb-id"/>
    <td>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </td>
  </xsl:template>

  <xsl:template match="tei:figure" mode="page">
    <xsl:param name="pb-id"/>
    <div class="ae-block ae-figure">
      <xsl:text>[Figure</xsl:text>
      <xsl:if test="normalize-space(tei:figDesc)">: <xsl:value-of select="normalize-space(tei:figDesc)"/></xsl:if>
      <xsl:text>] </xsl:text>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </div>
  </xsl:template>

  <xsl:template match="tei:note" mode="page">
    <xsl:param name="pb-id"/>
    <span class="ae-note">
      <xsl:text> [Note: </xsl:text>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
      <xsl:text>] </xsl:text>
    </span>
  </xsl:template>

  <!--
    Line breaks: a <br/> before each line except the first of a block (transcriptions put <lb/> at
    the start of a line), the first after a page break (the line starts the page box) and one
    after a block-level sibling, which ends its line already.
  -->
  <xsl:template match="tei:lb" mode="page">
    <xsl:variable name="before" select="preceding-sibling::node()[self::* or normalize-space()][1]"/>
    <xsl:if test="$before and not($before[self::tei:pb or self::tei:cb or self::tei:head or self::tei:p or self::tei:ab or self::tei:dateline or self::tei:salute or self::tei:signed or self::tei:addrLine or self::tei:fw or self::tei:list or self::tei:table or self::tei:figure])">
      <br/>
    </xsl:if>
  </xsl:template>

  <!-- editorial markup -->

  <xsl:template match="tei:unclear" mode="page">
    <xsl:param name="pb-id"/>
    <span class="ae-unclear" title="unclear">
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </span>
  </xsl:template>

  <xsl:template match="tei:gap" mode="page">
    <span class="ae-gap">
      <xsl:attribute name="title">
        <xsl:value-of select="normalize-space(concat('omitted ', @reason, ' ', @quantity, ' ', @unit, ' ', @extent))"/>
      </xsl:attribute>
      <xsl:text>[…]</xsl:text>
    </span>
  </xsl:template>

  <xsl:template match="tei:space" mode="page">
    <xsl:text>&#160;&#160;&#160;&#160;</xsl:text>
  </xsl:template>

  <xsl:template match="tei:supplied" mode="page">
    <xsl:param name="pb-id"/>
    <span class="ae-supplied" title="supplied by the editor">
      <xsl:text>[</xsl:text>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
      <xsl:text>]</xsl:text>
    </span>
  </xsl:template>

  <xsl:template match="tei:damage" mode="page">
    <xsl:param name="pb-id"/>
    <span class="ae-damage" title="damaged">
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </span>
  </xsl:template>

  <xsl:template match="tei:del" mode="page">
    <xsl:param name="pb-id"/>
    <del>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </del>
  </xsl:template>

  <xsl:template match="tei:add" mode="page">
    <xsl:param name="pb-id"/>
    <ins>
      <xsl:if test="@place"><xsl:attribute name="title">added <xsl:value-of select="@place"/></xsl:attribute></xsl:if>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </ins>
  </xsl:template>

  <xsl:template match="tei:hi" mode="page">
    <xsl:param name="pb-id"/>
    <xsl:choose>
      <xsl:when test="contains(@rend, 'underline')">
        <u><xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template></u>
      </xsl:when>
      <xsl:when test="contains(@rend, 'bold')">
        <b><xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template></b>
      </xsl:when>
      <xsl:when test="contains(@rend, 'sup')">
        <sup><xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template></sup>
      </xsl:when>
      <xsl:otherwise>
        <i><xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template></i>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

  <xsl:template match="tei:foreign" mode="page">
    <xsl:param name="pb-id"/>
    <i>
      <xsl:call-template name="children"><xsl:with-param name="pb-id" select="$pb-id"/></xsl:call-template>
    </i>
  </xsl:template>

  <!--
    <choice>: show the corrected, regularized or expanded reading; the original is the tooltip.
    Readings of a <choice> do not cross page breaks, so they are output as a whole.
  -->
  <xsl:template match="tei:choice" mode="page">
    <xsl:param name="pb-id"/>
    <xsl:variable name="shown" select="(tei:corr | tei:reg | tei:expan)[1]"/>
    <xsl:variable name="alt" select="(tei:sic | tei:orig | tei:abbr)[1]"/>
    <xsl:choose>
      <xsl:when test="$shown and $alt">
        <span class="ae-alt" title="{normalize-space($alt)}">
          <xsl:apply-templates select="$shown/node()" mode="page">
            <xsl:with-param name="pb-id" select="$pb-id"/>
          </xsl:apply-templates>
        </span>
      </xsl:when>
      <xsl:otherwise>
        <xsl:apply-templates select="*[1]/node()" mode="page">
          <xsl:with-param name="pb-id" select="$pb-id"/>
        </xsl:apply-templates>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>

</xsl:stylesheet>
