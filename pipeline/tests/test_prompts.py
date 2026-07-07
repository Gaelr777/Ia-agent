from pipeline.cv_classifier import prompts


def test_build_system_prompt_embeds_full_sector_catalog():
    system_prompt = prompts.build_system_prompt()
    assert "31-33" in system_prompt
    assert "Industrias manufactureras" in system_prompt


def test_build_user_message_includes_cv_text():
    message = prompts.build_user_message("Experiencia como operador de producción en planta automotriz.")
    assert "operador de producción" in message


def test_build_user_message_truncates_long_cv_text():
    long_text = "a" * 20000
    message = prompts.build_user_message(long_text)
    cv_portion = message.split("\n\n", 1)[1]
    assert cv_portion == "a" * 12000
