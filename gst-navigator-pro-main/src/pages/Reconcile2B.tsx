import { useState, useRef } from 'react';
import { useApp } from '@/context/AppContext';
import { serviceGet, servicePostFormData } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { MetricCard, MetricGrid } from '@/components/dashboard/MetricCard';
import { DataTable } from '@/components/dashboard/DataTable';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Upload, Download, FileText, CheckCircle2, XCircle, Loader2, RefreshCw, Columns } from 'lucide-react';

interface SectionResult {
  summary: Record<string, number>;
  matched: Record<string, any>[];
  un_books: Record<string, any>[];
  un_2b: Record<string, any>[];
}

interface ReconciliationResult {
  success: boolean;
  b2b: SectionResult;
  cdnr: SectionResult;
  combined_summary: Record<string, number>;
  excel_base64: string;
  html_report: string;
}

interface Check2BInfo {
  available: boolean;
  record_count: number;
  b2b_count: number;
  cdnr_count: number;
  response_type: string | null;
  gen_date: string | null;
}

interface ExtractColumnsResult {
  books_columns: string[];
  t2b_columns: string[];
  books_mapping: Record<string, string>;
  t2b_mapping: Record<string, string>;
  required_fields: string[];
}

const REQUIRED_FIELDS = ["GSTIN", "Party Name", "Invoice No", "Invoice Date",
                         "Taxable Value", "CGST", "SGST", "IGST"];

const MATCHED_COLUMNS = [
  { key: 'GSTIN', label: 'GSTIN', type: 'text' as const },
  { key: 'Party Name', label: 'Party Name', type: 'text' as const },
  { key: 'Books Invoice No.', label: 'Books Inv #', type: 'text' as const },
  { key: '2B Invoice No.', label: '2B Inv #', type: 'text' as const },
  { key: 'Match Score', label: 'Score', type: 'number' as const },
  { key: 'Taxable Amt.', label: 'Taxable', type: 'currency' as const },
  { key: 'Total Tax', label: 'Books Tax', type: 'currency' as const },
  { key: '2B Total Tax', label: '2B Tax', type: 'currency' as const },
  { key: 'Tax Diff', label: 'Tax Diff', type: 'currency' as const },
  { key: 'Category', label: 'Category', type: 'text' as const },
];

const UNMATCHED_COLUMNS = [
  { key: 'GSTIN', label: 'GSTIN', type: 'text' as const },
  { key: 'Party Name', label: 'Party Name', type: 'text' as const },
  { key: 'Invoice No', label: 'Invoice #', type: 'text' as const },
  { key: 'Invoice Date', label: 'Date', type: 'text' as const },
  { key: 'Taxable Value', label: 'Taxable', type: 'currency' as const },
  { key: 'CGST', label: 'CGST', type: 'currency' as const },
  { key: 'SGST', label: 'SGST', type: 'currency' as const },
  { key: 'IGST', label: 'IGST', type: 'currency' as const },
];

export default function Reconcile2B() {
  const { activeClient, state } = useApp();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [check2b, setCheck2b] = useState<Check2BInfo | null>(null);
  const [checkLoading, setCheckLoading] = useState(false);
  const [fetchingFresh, setFetchingFresh] = useState(false);
  const [booksFile, setBooksFile] = useState<File | null>(null);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ReconciliationResult | null>(null);

  // Column mapping state
  const [extracting, setExtracting] = useState(false);
  const [showMapping, setShowMapping] = useState(false);
  const [booksColumns, setBooksColumns] = useState<string[]>([]);
  const [t2bColumns, setT2bColumns] = useState<string[]>([]);
  const [booksMapping, setBooksMapping] = useState<Record<string, string>>({});
  const [t2bMapping, setT2bMapping] = useState<Record<string, string>>({});

  const gstin = activeClient?.gstin;
  const period = state.selectedPeriod;

  const handleCheck2B = async () => {
    if (!gstin || !period) return;
    setCheckLoading(true);
    try {
      const info = await serviceGet(`/reconciliation/check-2b/${gstin}/${period.year}/${period.month}`);
      setCheck2b(info);
    } catch (err: any) {
      toast({ title: 'Check failed', description: err?.message || 'Could not check 2B data', variant: 'destructive' });
    } finally {
      setCheckLoading(false);
    }
  };

  const handleFetchFresh = async () => {
    if (!gstin || !period) return;
    setFetchingFresh(true);
    try {
      await serviceGet(`/gstr2B/gstr2b/${gstin}/${period.year}/${period.month}`);
      toast({ title: '2B data fetched', description: 'Fresh 2B data has been fetched and stored.' });
      await handleCheck2B();
    } catch (err: any) {
      toast({ title: 'Fetch failed', description: err?.message || 'Could not fetch 2B data', variant: 'destructive' });
    } finally {
      setFetchingFresh(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setBooksFile(file);
    // Reset mapping when a new file is chosen
    setShowMapping(false);
    setBooksColumns([]);
    setT2bColumns([]);
    setBooksMapping({});
    setT2bMapping({});
    setResult(null);
  };

  const handleExtractColumns = async () => {
    if (!gstin || !period || !booksFile) return;
    setExtracting(true);
    try {
      const formData = new FormData();
      formData.append('books_file', booksFile);
      const res: ExtractColumnsResult = await servicePostFormData(
        `/reconciliation/extract-columns/${gstin}/${period.year}/${period.month}`,
        formData
      );
      setBooksColumns(res.books_columns);
      setT2bColumns(res.t2b_columns);
      setBooksMapping(res.books_mapping);  // {standard_field: original_col}
      setT2bMapping(res.t2b_mapping);
      setShowMapping(true);
      toast({ title: 'Columns extracted', description: `${res.books_columns.length} books columns, ${res.t2b_columns.length} 2B columns.` });
    } catch (err: any) {
      toast({ title: 'Extract failed', description: err?.message || 'Could not extract columns', variant: 'destructive' });
    } finally {
      setExtracting(false);
    }
  };

  const handleRunReconciliation = async () => {
    if (!gstin || !period || !booksFile) return;
    setRunning(true);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append('books_file', booksFile);
      // Send column mappings if available
      if (showMapping) {
        formData.append('books_mapping_json', JSON.stringify(booksMapping));
        formData.append('t2b_mapping_json', JSON.stringify(t2bMapping));
      }
      const res = await servicePostFormData(
        `/reconciliation/run/${gstin}/${period.year}/${period.month}`,
        formData
      );
      setResult(res);
      const b2bCount = res.b2b?.summary?.matched_count || 0;
      const cdnrCount = res.cdnr?.summary?.matched_count || 0;
      toast({ title: 'Reconciliation complete', description: `Matched ${b2bCount} B2B + ${cdnrCount} CDNR records.` });
    } catch (err: any) {
      toast({ title: 'Reconciliation failed', description: err?.message || 'Error running reconciliation', variant: 'destructive' });
    } finally {
      setRunning(false);
    }
  };

  const downloadExcel = () => {
    if (!result?.excel_base64) return;
    const byteChars = atob(result.excel_base64);
    const byteNumbers = new Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) {
      byteNumbers[i] = byteChars.charCodeAt(i);
    }
    const blob = new Blob([new Uint8Array(byteNumbers)], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Reconciliation_${gstin}_${period?.year}-${period?.month}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadHtml = () => {
    if (!result?.html_report) return;
    const blob = new Blob([result.html_report], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Reconciliation_${gstin}_${period?.year}-${period?.month}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col min-w-0">
        <TopBar />
        <ScrollArea className="flex-1">
          <div className="p-6 max-w-[1400px] mx-auto space-y-6">
            <h1 className="text-xl font-bold">GSTR-2B Reconciliation</h1>

            {!activeClient ? (
              <div className="flex items-center justify-center h-[40vh]">
                <p className="text-sm text-muted-foreground">Select a client from the sidebar to begin</p>
              </div>
            ) : !period ? (
              <div className="flex items-center justify-center h-[40vh]">
                <p className="text-sm text-muted-foreground">Select a period first</p>
              </div>
            ) : (
              <>
                {/* 2B Data Status Panel */}
                <div className="rounded-lg border bg-card p-4 space-y-3">
                  <h2 className="text-sm font-semibold">2B Data Status — {period.month}/{period.year}</h2>
                  <div className="flex items-center gap-3">
                    <Button size="sm" variant="outline" onClick={handleCheck2B} disabled={checkLoading}>
                      {checkLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <RefreshCw className="h-3.5 w-3.5 mr-1.5" />}
                      Check 2B Data
                    </Button>
                    <Button size="sm" variant="secondary" onClick={handleFetchFresh} disabled={fetchingFresh}>
                      {fetchingFresh ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Download className="h-3.5 w-3.5 mr-1.5" />}
                      Fetch Fresh 2B Data
                    </Button>
                  </div>
                  {check2b && (
                    <div className="flex items-center gap-4 text-sm">
                      {check2b.available ? (
                        <>
                          <span className="flex items-center gap-1 text-green-600"><CheckCircle2 className="h-4 w-4" /> Available</span>
                          <span>{check2b.record_count} records ({check2b.b2b_count} B2B, {check2b.cdnr_count} CDNR)</span>
                          {check2b.response_type && <span className="text-muted-foreground">Type: {check2b.response_type}</span>}
                          {check2b.gen_date && <span className="text-muted-foreground">Generated: {check2b.gen_date}</span>}
                        </>
                      ) : (
                        <span className="flex items-center gap-1 text-red-500"><XCircle className="h-4 w-4" /> No 2B data for this period</span>
                      )}
                    </div>
                  )}
                </div>

                {/* Books Upload Panel */}
                <div className="rounded-lg border bg-card p-4 space-y-3">
                  <h2 className="text-sm font-semibold">Upload Books (Purchase Register)</h2>
                  <div className="flex items-center gap-3">
                    <Button size="sm" variant="outline" onClick={() => fileInputRef.current?.click()}>
                      <Upload className="h-3.5 w-3.5 mr-1.5" /> Choose Excel File
                    </Button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".xlsx,.xls"
                      onChange={handleFileChange}
                      className="hidden"
                    />
                    {booksFile && (
                      <span className="text-sm text-muted-foreground">
                        {booksFile.name} ({(booksFile.size / 1024).toFixed(1)} KB)
                      </span>
                    )}
                    {booksFile && check2b?.available && !showMapping && (
                      <Button size="sm" variant="secondary" onClick={handleExtractColumns} disabled={extracting}>
                        {extracting ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Columns className="h-3.5 w-3.5 mr-1.5" />}
                        Extract & Map Columns
                      </Button>
                    )}
                  </div>
                </div>

                {/* Column Mapping Panel */}
                {showMapping && (
                  <div className="rounded-lg border bg-card p-4 space-y-4">
                    <h2 className="text-sm font-semibold">Map Headers</h2>
                    <p className="text-xs text-muted-foreground">
                      Verify column mappings below. The system auto-detected the best matches. Override any incorrect mappings.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* Books Column Mapping */}
                      <div className="space-y-3">
                        <h3 className="text-xs font-semibold uppercase text-muted-foreground">Books Headers</h3>
                        {REQUIRED_FIELDS.map((field) => (
                          <div key={`b_${field}`} className="space-y-1">
                            <Label className="text-xs">{field}</Label>
                            <select
                              className="w-full rounded-md border bg-background px-3 py-1.5 text-sm"
                              value={booksMapping[field] || ''}
                              onChange={(e) => setBooksMapping({ ...booksMapping, [field]: e.target.value })}
                            >
                              <option value="">— Not mapped —</option>
                              {booksColumns.map((col) => (
                                <option key={col} value={col}>{col}</option>
                              ))}
                            </select>
                          </div>
                        ))}
                      </div>
                      {/* 2B Column Mapping */}
                      <div className="space-y-3">
                        <h3 className="text-xs font-semibold uppercase text-muted-foreground">2B Headers</h3>
                        {REQUIRED_FIELDS.map((field) => (
                          <div key={`t_${field}`} className="space-y-1">
                            <Label className="text-xs">{field}</Label>
                            <select
                              className="w-full rounded-md border bg-background px-3 py-1.5 text-sm"
                              value={t2bMapping[field] || ''}
                              onChange={(e) => setT2bMapping({ ...t2bMapping, [field]: e.target.value })}
                            >
                              <option value="">— Not mapped —</option>
                              {t2bColumns.map((col) => (
                                <option key={col} value={col}>{col}</option>
                              ))}
                            </select>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Run Button */}
                <div className="flex items-center gap-3">
                  <Button
                    onClick={handleRunReconciliation}
                    disabled={running || !booksFile || !check2b?.available}
                  >
                    {running ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <FileText className="h-4 w-4 mr-2" />}
                    {showMapping ? 'Confirm & Run Reconciliation' : 'Run Reconciliation'}
                  </Button>
                  {!check2b?.available && booksFile && (
                    <span className="text-xs text-muted-foreground">Check or fetch 2B data first</span>
                  )}
                  {showMapping && (
                    <Button variant="ghost" size="sm" onClick={() => setShowMapping(false)}>
                      Skip Mapping
                    </Button>
                  )}
                </div>

                {/* Results */}
                {result && (
                  <div className="space-y-6">
                    {/* Combined Summary Metrics */}
                    <div>
                      <h2 className="text-sm font-semibold mb-2">Combined Summary</h2>
                      <MetricGrid>
                        <MetricCard label="Books Total ITC" value={result.combined_summary.books_total_itc} isCurrency />
                        <MetricCard label="2B Total ITC" value={result.combined_summary.t2b_total_itc} isCurrency />
                        <MetricCard label="Matched ITC" value={result.combined_summary.matched_itc} isCurrency />
                        <MetricCard label="Books Risk ITC" value={result.combined_summary.books_risk_itc} isCurrency />
                        <MetricCard label="2B Risk ITC" value={result.combined_summary.t2b_risk_itc} isCurrency />
                        <MetricCard label="Matched" value={result.combined_summary.matched_count} />
                        <MetricCard label="Books Invoices" value={result.combined_summary.books_invoice_count} />
                        <MetricCard label="2B Invoices" value={result.combined_summary.t2b_invoice_count} />
                        <MetricCard label="Books Not in 2B" value={result.combined_summary.un_books_count} />
                        <MetricCard label="2B Not in Books" value={result.combined_summary.un_2b_count} />
                      </MetricGrid>
                    </div>

                    {/* Download Buttons */}
                    <div className="flex gap-3">
                      <Button variant="outline" size="sm" onClick={downloadExcel}>
                        <Download className="h-3.5 w-3.5 mr-1.5" /> Download Excel Report
                      </Button>
                      <Button variant="outline" size="sm" onClick={downloadHtml}>
                        <FileText className="h-3.5 w-3.5 mr-1.5" /> Download HTML Report
                      </Button>
                    </div>

                    {/* B2B / CDNR Section Tabs */}
                    <Tabs defaultValue="b2b" className="w-full">
                      <TabsList>
                        <TabsTrigger value="b2b">B2B Invoices</TabsTrigger>
                        <TabsTrigger value="cdnr">CDNR Notes</TabsTrigger>
                      </TabsList>

                      {/* B2B Section */}
                      <TabsContent value="b2b" className="space-y-4">
                        <div>
                          <h3 className="text-xs font-semibold uppercase text-muted-foreground mb-2">B2B Summary</h3>
                          <MetricGrid>
                            <MetricCard label="Books ITC" value={result.b2b.summary.books_total_itc} isCurrency />
                            <MetricCard label="2B ITC" value={result.b2b.summary.t2b_total_itc} isCurrency />
                            <MetricCard label="Matched" value={result.b2b.summary.matched_count} />
                            <MetricCard label="Books Risk" value={result.b2b.summary.books_risk_itc} isCurrency />
                            <MetricCard label="2B Risk" value={result.b2b.summary.t2b_risk_itc} isCurrency />
                          </MetricGrid>
                        </div>
                        <Tabs defaultValue="b2b_matched" className="w-full">
                          <TabsList>
                            <TabsTrigger value="b2b_matched">Matched ({result.b2b.matched.length})</TabsTrigger>
                            <TabsTrigger value="b2b_un_books">Books Not in 2B ({result.b2b.un_books.length})</TabsTrigger>
                            <TabsTrigger value="b2b_un_2b">2B Not in Books ({result.b2b.un_2b.length})</TabsTrigger>
                          </TabsList>
                          <TabsContent value="b2b_matched">
                            <DataTable columns={MATCHED_COLUMNS} data={result.b2b.matched} />
                          </TabsContent>
                          <TabsContent value="b2b_un_books">
                            <DataTable columns={UNMATCHED_COLUMNS} data={result.b2b.un_books} />
                          </TabsContent>
                          <TabsContent value="b2b_un_2b">
                            <DataTable columns={UNMATCHED_COLUMNS} data={result.b2b.un_2b} />
                          </TabsContent>
                        </Tabs>
                      </TabsContent>

                      {/* CDNR Section */}
                      <TabsContent value="cdnr" className="space-y-4">
                        <div>
                          <h3 className="text-xs font-semibold uppercase text-muted-foreground mb-2">CDNR Summary</h3>
                          <MetricGrid>
                            <MetricCard label="Books ITC" value={result.cdnr.summary.books_total_itc} isCurrency />
                            <MetricCard label="2B ITC" value={result.cdnr.summary.t2b_total_itc} isCurrency />
                            <MetricCard label="Matched" value={result.cdnr.summary.matched_count} />
                            <MetricCard label="Books Risk" value={result.cdnr.summary.books_risk_itc} isCurrency />
                            <MetricCard label="2B Risk" value={result.cdnr.summary.t2b_risk_itc} isCurrency />
                          </MetricGrid>
                        </div>
                        <Tabs defaultValue="cdnr_matched" className="w-full">
                          <TabsList>
                            <TabsTrigger value="cdnr_matched">Matched ({result.cdnr.matched.length})</TabsTrigger>
                            <TabsTrigger value="cdnr_un_books">Books Not in 2B ({result.cdnr.un_books.length})</TabsTrigger>
                            <TabsTrigger value="cdnr_un_2b">2B Not in Books ({result.cdnr.un_2b.length})</TabsTrigger>
                          </TabsList>
                          <TabsContent value="cdnr_matched">
                            <DataTable columns={MATCHED_COLUMNS} data={result.cdnr.matched} />
                          </TabsContent>
                          <TabsContent value="cdnr_un_books">
                            <DataTable columns={UNMATCHED_COLUMNS} data={result.cdnr.un_books} />
                          </TabsContent>
                          <TabsContent value="cdnr_un_2b">
                            <DataTable columns={UNMATCHED_COLUMNS} data={result.cdnr.un_2b} />
                          </TabsContent>
                        </Tabs>
                      </TabsContent>
                    </Tabs>
                  </div>
                )}
              </>
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
