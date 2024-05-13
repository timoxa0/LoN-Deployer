from lon_deployer import files


def test_ofox() -> None:
    file = files.OrangeFox
    assert file.name == "orangefox.img"
    assert file.md5sum() == "3edc8c32db0384006caf8cf066257811"

