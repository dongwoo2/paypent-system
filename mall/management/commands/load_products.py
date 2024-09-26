from django.core.files.base import ContentFile
from django.core.management import BaseCommand
import requests
from dataclasses import dataclass
from mall.models import Category, Product
from tqdm import tqdm

BASE_URL = "https://raw.githubusercontent.com/pyhub-kr/dump-data/main/django-shopping-with-iamport/"


@dataclass
class Item:
    category_name: str
    name: str
    price: int
    priceUnit: str
    desc: str
    photo_path: str


class Command(BaseCommand):
    help = "Load products from JSON file"

    def handle(self, *args, **options):
        json_url = BASE_URL + "product-list.json"
        item_dict_list = requests.get(json_url).json()

        # list comprehension 문법 append 되는 대상을 for 앞에 쓰고
        # 대괄호로 묶어서 item_list를 정의 할 수 도 있다

        # item_list2 = []
        # for item_dict in item_dict_list:
        #   item_list2 = Item(**item_dict)

        item_list = [Item(**item_dict) for item_dict in item_dict_list]

        # set comprehension 문법으로 item_list에서 category_name 값 만으로 구성된 새로운 집합을 만듭니다.
        category_name_set = {item.category_name for item in item_list}
        print(category_name_set)  # set이니까 중복알아서 제거 됨

        category_dict = {}
        # 카테고리만 생성하는 거
        for category_name in category_name_set:
            # 이름이 없으면 미분류 이름이 없으면 false니까 or가서 미분류로 값 설정
            # get_or_create 지금 반환인자가 2개인데 category에 담고 하나는 안 쓰겠따 해서 언더바 선언
            category, __ = Category.objects.get_or_create(
                name=category_name or "미분류"
            )
            category_dict[category.name] = category

        # Product 모델의 category 외래키 지정을 위해서,
        # item.category_name 속성을 Key로 해서 category_dict에서 Category 인스턴스를 획득해야함
        for item in tqdm(item_list):
            # item.category_name이 존재하면 그 값을 사용하고, 없으면 "미분류"라는 문자열을 사용하여
            # category_dict에서 해당 카테고리를 가져옵니다. 이 값을 category라는 변수에 저장합니다.
            # 만약에 category_dict[category_name] 하고 != item.category_name이면 미분류로 들어가는거임 아무튼
            # 값이 같으니까 쓰는 거
            category: Category = category_dict[item.category_name or "미분류"]
            # Product 모델에서 get_or_create 메소드를 사용하여 주어진 조건에 맞는 제품을 조회하거나, 없으면 새로 생성합니다.
            # 결과는 product 변수에 제품 객체를, is_created 변수에는 새로 생성되었는지를 불리언 값으로 저장합니다.
            product, is_created = Product.objects.get_or_create(
                # get_or_create 메소드에 전달하는 category와 name은 제품을 조회하는 데 사용됩니다.
                # 이 두 인자를 기준으로 데이터베이스에서 기존의 제품을 찾습니다.
                # 조회해서 안나올경우 defaults 에서 추가로 설정할 기본값들을 사용한다
                category=category,
                name=item.name,
                defaults={  # 제품이 생성 될 경우 추가로 설정할 기본값들을 지정
                    "description": item.desc,
                    "price": item.price,
                },
            )
            if is_created:  # 생성 되었을 경우에 값 지정 해서 save
                photo_url = BASE_URL + item.photo_path
                filename = photo_url.rsplit("/", 1)[-1]
                photo_data = requests.get(
                    photo_url
                ).content  # raw data # FIXME  멀티쓰레드 이용해서 이 부분 빠르게 해결해보자
                product.photo.save(
                    name=filename,
                    content=ContentFile(photo_data),
                    save=True,
                )
