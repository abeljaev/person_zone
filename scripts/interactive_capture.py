#!/usr/bin/env python3
"""
Интерактивный скрипт для выбора и захвата кадра из видео.
"""
import argparse
import sys
import cv2
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.video import VideoReader
from src.utils.logger import logger


def parse_args():

    parser = argparse.ArgumentParser(description="Интерактивный выбор кадра из видео")

    parser.add_argument(
        "-s",
        "--source",
        type=str,
        default="test_video/video.mkv",
        help="Путь к видеофайлу",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="test_imgs/frame.jpg",
        help="Путь для сохранения выбранного кадра",
    )

    return parser.parse_args()


def main():

    args = parse_args()

    # Создаем экземпляр VideoReader
    video_reader = VideoReader(args.source)

    # Открываем видеопоток
    if not video_reader.open():
        logger.error("Не удалось открыть видеопоток")
        return 1

    print("=== Интерактивный выбор кадра ===")
    print("Управление:")
    print("- ПРОБЕЛ: сохранить текущий кадр и выйти")
    print("- ESC или 'q': выйти без сохранения")
    print("- Любая другая клавиша: следующий кадр")
    print("=====================================")

    window_name = "Выбор кадра - нажмите ПРОБЕЛ для сохранения"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    frame_saved = False
    current_frame = None

    try:
        while True:

            success, frame = video_reader.read_frame()

            if not success:
                logger.warning("Достигнут конец видео или ошибка чтения")
                break

            current_frame = frame.copy()

            info_text = (
                f"Кадр: {video_reader.current_frame_index}/{video_reader.frame_count}"
            )
            cv2.putText(
                frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
            )

            cv2.putText(
                frame,
                "ПРОБЕЛ - сохранить, ESC/Q - выйти",
                (10, frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )

            cv2.imshow(window_name, frame)

            key = cv2.waitKey(30) & 0xFF

            if key == ord(" "):
                if current_frame is not None:
                    output_path = Path(args.output)
                    try:

                        output_path.parent.mkdir(parents=True, exist_ok=True)

                        if cv2.imwrite(str(output_path), current_frame):
                            logger.info(
                                f"Кадр {video_reader.current_frame_index} сохранен в {output_path}"
                            )
                            print(f"\nКадр сохранен: {output_path}")
                            frame_saved = True
                            break
                        else:
                            logger.error(f"Не удалось сохранить кадр в {output_path}")
                    except Exception as e:
                        logger.error(f"Ошибка при сохранении кадра: {str(e)}")

            elif key == 27 or key == ord("q"):
                print("\nВыход без сохранения")
                break

    except KeyboardInterrupt:
        print("\nПрервано пользователем")

    finally:
        video_reader.close()
        cv2.destroyAllWindows()

    if frame_saved:
        print("Кадр успешно выбран и сохранен!")
        return 0
    else:
        print("Кадр не был сохранен")
        return 1


if __name__ == "__main__":
    sys.exit(main())
