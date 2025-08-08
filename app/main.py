
from app.translator import translate_xml_to_openai


def main() -> None:
    sample = """Hello user
<tool_call><function=say_hello><parameter=name>John</parameter></function></tool_call>"""
    
    result = translate_xml_to_openai(sample)
    print(result.model_dump_json(indent=2))


if __name__ == '__main__':
    main()