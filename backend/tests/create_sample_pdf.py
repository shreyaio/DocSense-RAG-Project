import fitz

def create_sample_pdf(path: str):
    doc = fitz.open()
    
    # Page 1
    page1 = doc.new_page()
    page1.insert_text((50, 50), "Introduction to RAG", fontsize=20)
    page1.insert_text((50, 100), "This is a document about Retrieval Augmented Generation.", fontsize=12)
    page1.insert_text((50, 130), "Section 1: Architecture", fontsize=16)
    page1.insert_text((50, 160), "The architecture consists of an ingestion pipeline and a retrieval pipeline.", fontsize=12)
    
    # Page 2
    page2 = doc.new_page()
    page2.insert_text((50, 50), "Section 2: Benefits", fontsize=16)
    page2.insert_text((50, 80), "RAG reduces hallucinations by grounding the model in factual data.", fontsize=12)
    page2.insert_text((50, 110), "It allows for easy updates of the knowledge base without retraining.", fontsize=12)
    
    doc.save(path)
    doc.close()

if __name__ == "__main__":
    create_sample_pdf("sample.pdf")
    print("Created sample.pdf")
