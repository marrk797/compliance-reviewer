declare module "mammoth/mammoth.browser" {
  interface ExtractRawTextOptions {
    arrayBuffer: ArrayBuffer;
  }
  interface ExtractRawTextResult {
    value: string;
    messages: Array<{ type: string; message: string }>;
  }
  export function extractRawText(
    options: ExtractRawTextOptions,
  ): Promise<ExtractRawTextResult>;
}
