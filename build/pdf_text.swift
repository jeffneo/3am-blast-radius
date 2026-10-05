// Print the text macOS (PDFKit, i.e. Preview, Safari and Quick Look) would copy out of a PDF.
//   swift build/pdf_text.swift LAB-GUIDE.pdf
import PDFKit
guard CommandLine.arguments.count > 1, let doc = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])) else {
    FileHandle.standardError.write("usage: pdf_text.swift file.pdf\n".data(using: .utf8)!)
    exit(2)
}
print(doc.string ?? "")
