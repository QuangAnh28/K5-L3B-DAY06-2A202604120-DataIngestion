"""Create validated corpus artifacts and a benchmark BEFORE retrieval. Run from starter."""
import sys, json, re, hashlib
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ingestion import load_pdf

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'https://ipvietnam.gov.vn/documents/20182/1226838/5.11.+Luat+Thuong+mai+2005.pdf/abd363d4-2646-48d5-a2db-4d42f231578e'
DOC = 'luat-thuong-mai-36-2005-qh11'
def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def main():
    pdf = ROOT/'starter/data/luat_thuong_mai_2005.pdf'
    pages = load_pdf(pdf, DOC, SOURCE)
    save(ROOT/'starter/results/pages.json', [dict(page=p.page,text=p.text,metadata=p.metadata) for p in pages])
    useful = [p.page for p in pages if len(p.text)>100 and p.page<84]
    save(ROOT/'data/manifest.json', dict(source_id=DOC, title='Luật Thương mại 36/2005/QH11',
       source_path_or_url=SOURCE, local_path='starter/data/luat_thuong_mai_2005.pdf',
       accessed_at=datetime.now(timezone.utc).isoformat(), sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
       snapshot='Văn bản năm 2005; không khẳng định là bản hợp nhất hiện hành',
       license_or_permission='Văn bản quy phạm pháp luật tiếng Việt; căn cứ Điều 15 khoản 2 Luật SHTT về đối tượng không thuộc phạm vi bảo hộ quyền tác giả. Nguồn công bố: Cục SHTT.',
       physical_pages=len(pages), counted_pages=useful, excluded_pages=[84],
       counting_rule='Trang 1–83 có nội dung điều luật; loại trang 84 chỉ có tên người ký. Không nhân bản.',
       pages=[dict(page=p.page,characters=len(p.text),counted=p.page in useful) for p in pages]))
    rows = [
      (7,'Thương nhân chưa đăng ký kinh doanh có còn phải chịu trách nhiệm về hoạt động của mình không?', 'Có, vẫn phải chịu trách nhiệm theo Luật này và quy định khác của pháp luật.',0),
      (10,'Nguyên tắc bình đẳng áp dụng thế nào với thương nhân thuộc các thành phần kinh tế?', 'Mọi thành phần kinh tế bình đẳng trước pháp luật trong hoạt động thương mại.',0),
      (15,'Khi nào thông điệp dữ liệu có giá trị pháp lý tương đương văn bản?', 'Khi đáp ứng các điều kiện và tiêu chuẩn kỹ thuật theo quy định pháp luật.',0),
      (18,'Văn phòng đại diện có được hoạt động sinh lợi trực tiếp tại Việt Nam không?', 'Không được thực hiện hoạt động sinh lợi trực tiếp tại Việt Nam.',1),
      (24,'Trong phạm vi Chương II, hợp đồng mua bán hàng hóa có những hình thức nào?', 'Lời nói, văn bản hoặc hành vi cụ thể.',1),
      (27,'Mua bán hàng hóa quốc tế phải dựa trên hợp đồng có hình thức nào?', 'Văn bản hoặc hình thức khác có giá trị pháp lý tương đương.',2),
      (35,'Nếu đã thỏa thuận địa điểm giao hàng, bên bán phải giao ở đâu?', 'Đúng địa điểm đã thỏa thuận.',1),
      (37,'Chỉ thỏa thuận thời hạn mà không chốt thời điểm giao hàng: bên bán được giao thế nào?', 'Bất kỳ thời điểm nào trong thời hạn đó và phải thông báo trước cho bên mua.',2),
      (50,'Nghĩa vụ cơ bản của bên mua về thanh toán và nhận hàng là gì?', 'Thanh toán tiền mua hàng và nhận hàng theo thỏa thuận.',1),
      (55,'Nếu không có thỏa thuận khác, khi nào bên mua phải thanh toán cho bên bán?', 'Khi bên bán giao hàng hoặc giao chứng từ liên quan đến hàng hóa.',-1),
      (57,'Nếu không có thỏa thuận khác và đã chốt địa điểm giao, rủi ro được chuyển khi nào?', 'Khi hàng đã giao cho bên mua hoặc người được ủy quyền nhận tại địa điểm đó, kể cả khi bên bán được ủy quyền giữ chứng từ sở hữu.',0),
      (62,'Nếu pháp luật và thỏa thuận không quy định khác, quyền sở hữu hàng hóa chuyển khi nào?', 'Kể từ thời điểm hàng hóa được chuyển giao.',0),
      (74,'Trong phạm vi Chương III, hợp đồng dịch vụ có thể được thể hiện bằng những hình thức nào?', 'Lời nói, văn bản hoặc hành vi cụ thể.',1),
      (86,'Không có thỏa thuận hay chỉ dẫn về giá dịch vụ thì xác định giá dựa trên căn cứ nào?', 'Giá loại dịch vụ đó trong các điều kiện tương tự về cung ứng, thời điểm, thị trường địa lý, thanh toán và điều kiện khác ảnh hưởng giá.',0),
      (87,'Không có thỏa thuận và không có thói quen thanh toán dịch vụ thì thời hạn thanh toán là khi nào?', 'Thời điểm việc cung ứng dịch vụ được hoàn thành.',0),
      (88,'Khuyến mại nhằm xúc tiến mua bán và cung ứng dịch vụ bằng cách nào?', 'Dành cho khách hàng những lợi ích nhất định.',1),
      (285,'Hợp đồng nhượng quyền thương mại phải có hình thức gì?', 'Văn bản hoặc hình thức khác có giá trị pháp lý tương đương.',0),
      (301,'Trong phạm vi Chương VII, mức phạt vi phạm hợp đồng bị giới hạn thế nào và có ngoại lệ nào?', 'Không quá 8% giá trị phần nghĩa vụ hợp đồng bị vi phạm, trừ trường hợp tại Điều 266.',0),
      (318,'Nếu không có thỏa thuận, thời hạn khiếu nại về số lượng hàng hóa là bao lâu và tính từ đâu? Có ngoại lệ dẫn chiếu nào?', 'Ba tháng kể từ ngày giao hàng; trừ trường hợp điểm đ khoản 1 Điều 237.',-1),
      (319,'Thời hiệu khởi kiện tranh chấp thương mại là bao lâu, tính từ khi nào và có ngoại lệ nào?', 'Hai năm kể từ khi quyền và lợi ích hợp pháp bị xâm phạm, trừ điểm e khoản 1 Điều 237.',0),
    ]
    questions=[]
    for i,(article,q,answer,clause) in enumerate(rows,1):
        page=next(p for p in pages if re.search(r'Điều\s+'+str(article)+r'\.',p.text))
        body=re.split(r'Điều\s+'+str(article)+r'\.',page.text,maxsplit=1)[1]
        body=re.split(r'\n\n(?:Điều\s+\d+\.|Mục\s+\d+|Chương\s+)',body)[0]
        parts=body.split('\n\n')
        if clause>0:
            quote=next(s for s in parts if s.startswith(str(clause)+'.'))
        elif clause==-1:
            quote='\n\n'.join(parts[:2])
        else:
            quote='\n\n'.join(parts[1:]) if len(parts)>1 else body
        assert quote.strip() in page.text, article
        filt={}
        if article in (24,74,301):
            filt={'chapter':{24:'Chương Ii',74:'Chương Iii',301:'Chương Vii'}[article]}
        questions.append(dict(id=f'q{i:02}',split='dev' if i<=15 else 'test',question=q,
                         expected_answer=answer,gold_source_id=DOC,gold_page=page.page,
                         evidence_quote=quote.strip(),filter=filt,article=article))
    target=ROOT/'benchmark/questions.json'
    if target.exists():
        assert json.loads(target.read_text(encoding='utf-8'))==questions, 'Benchmark is frozen; refusing changes'
    else: save(target,questions)
    print('Pages:',len(pages),'useful:',len(useful),'questions:',len(questions))

if __name__=='__main__': main()
