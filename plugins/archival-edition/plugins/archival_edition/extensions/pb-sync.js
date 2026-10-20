/**
 * Autosearch fallback for the archival edition.
 *
 * The photographed pages have no text layer, so the editor cannot find the text of the selected
 * node in the PDF. This extension answers the `pdfSearch.fallback` extension point with the page
 * of the nearest preceding <pb/>: the n-th <pb/> is the n-th photograph, which follows the pages
 * of the description form (header label "form-pages") at the start of the PDF.
 *
 * @import { PluginContext } from '../../../../app/src/modules/plugin-context.js'
 */

const TEI_NS = 'http://www.tei-c.org/ns/1.0';
const VARIANT_ID = 'archival-edition';

export default class ArchivalPbSyncExtension extends FrontendExtensionPlugin {
  static extensionPoints = ['pdfSearch.fallback'];

  /** @param {PluginContext} context */
  constructor(context) {
    super(context, { name: 'archival-edition-pb-sync' });
  }

  /**
   * Extension point handler for `pdfSearch.fallback`, invoked by the editor's ServicesPlugin when
   * the text of the selected node was not found in the PDF. Delegates to
   * {@link ArchivalPbSyncExtension.pageForNode}.
   * @param {Element} node - the selected XML node
   * @param {{xml: string|null, pageCount: number}} info - the loaded PDF's page count
   * @returns {{page: number}|null} 1-based PDF page, or null if this is not an archival edition document
   */
  ['pdfSearch.fallback'](node, { pageCount }) {
    const page = ArchivalPbSyncExtension.pageForNode(node, pageCount);
    return page ? { page } : null;
  }

  /**
   * The PDF page showing the start of a node: the photograph of the nearest preceding <pb/>
   * (or of the first <pb/> for content before it), after the form pages.
   * @param {Node} node
   * @param {number} pageCount - number of pages of the PDF
   * @returns {number|null} 1-based page, or null if the document is not an archival edition
   *   document, has no <pb/> or the page lies outside the PDF
   */
  static pageForNode(node, pageCount) {
    const doc = node.ownerDocument;
    if (!doc) return null;
    const labels = Array.from(doc.getElementsByTagNameNS(TEI_NS, 'label'));
    const label = (/** @type {string} */ type) => labels.find(l => l.getAttribute('type') === type)?.textContent?.trim();
    if (label('variant-id') !== VARIANT_ID) return null;
    const formPages = parseInt(label('form-pages') ?? '', 10);
    if (!Number.isInteger(formPages)) return null;

    const pbs = Array.from(doc.getElementsByTagNameNS(TEI_NS, 'pb'));
    if (pbs.length === 0) return null;
    // pbs are in document order; count those that precede the node and do not lie inside it
    const preceding = pbs.filter(pb => node.compareDocumentPosition(pb) & Node.DOCUMENT_POSITION_PRECEDING).length;
    const page = formPages + Math.max(preceding, 1);
    return page <= pageCount ? page : null;
  }
}
