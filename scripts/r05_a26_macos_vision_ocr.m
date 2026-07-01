#import <Foundation/Foundation.h>
#import <ImageIO/ImageIO.h>
#import <Vision/Vision.h>

static void failWithMessage(NSString *message) {
    fprintf(stderr, "%s\n", message.UTF8String);
    exit(2);
}

static NSArray<NSString *> *parseLanguages(NSString *raw) {
    NSMutableArray<NSString *> *languages = [NSMutableArray array];
    for (NSString *part in [raw componentsSeparatedByString:@","]) {
        NSString *value = [part stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceCharacterSet];
        if (value.length > 0) {
            [languages addObject:value];
        }
    }
    return languages;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc < 3 || argc > 4) {
            failWithMessage(@"Usage: r05_a26_macos_vision_ocr IMAGE_PATH accurate|fast [language_csv]");
        }

        NSString *imagePath = [NSString stringWithUTF8String:argv[1]];
        NSString *mode = [NSString stringWithUTF8String:argv[2]];
        if (![@[@"accurate", @"fast"] containsObject:mode]) {
            failWithMessage(@"Recognition mode must be 'accurate' or 'fast'.");
        }

        NSURL *imageURL = [NSURL fileURLWithPath:imagePath];
        CGImageSourceRef imageSource = CGImageSourceCreateWithURL((__bridge CFURLRef)imageURL, NULL);
        if (imageSource == NULL) {
            failWithMessage([NSString stringWithFormat:@"Cannot open image: %@", imagePath]);
        }
        CGImageRef image = CGImageSourceCreateImageAtIndex(imageSource, 0, NULL);
        CFRelease(imageSource);
        if (image == NULL) {
            failWithMessage([NSString stringWithFormat:@"Cannot decode image: %@", imagePath]);
        }

        VNRecognizeTextRequest *request = [[VNRecognizeTextRequest alloc] init];
        request.recognitionLevel = [mode isEqualToString:@"accurate"]
            ? VNRequestTextRecognitionLevelAccurate
            : VNRequestTextRecognitionLevelFast;
        request.usesLanguageCorrection = YES;
        if (argc == 4) {
            NSArray<NSString *> *languages = parseLanguages([NSString stringWithUTF8String:argv[3]]);
            if (languages.count > 0) {
                request.recognitionLanguages = languages;
            }
        }

        VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:image options:@{}];
        NSError *performError = nil;
        BOOL performed = [handler performRequests:@[request] error:&performError];
        CGImageRelease(image);
        if (!performed || performError != nil) {
            failWithMessage([NSString stringWithFormat:@"Vision OCR failed: %@", performError]);
        }

        NSArray<VNRecognizedTextObservation *> *observations = request.results ?: @[];
        observations = [observations sortedArrayUsingComparator:^NSComparisonResult(
            VNRecognizedTextObservation *left,
            VNRecognizedTextObservation *right
        ) {
            CGFloat leftTop = CGRectGetMaxY(left.boundingBox);
            CGFloat rightTop = CGRectGetMaxY(right.boundingBox);
            if (fabs(leftTop - rightTop) > 0.01) {
                return leftTop > rightTop ? NSOrderedAscending : NSOrderedDescending;
            }
            CGFloat leftX = CGRectGetMinX(left.boundingBox);
            CGFloat rightX = CGRectGetMinX(right.boundingBox);
            if (leftX == rightX) {
                return NSOrderedSame;
            }
            return leftX < rightX ? NSOrderedAscending : NSOrderedDescending;
        }];

        NSMutableArray<NSDictionary *> *lines = [NSMutableArray array];
        NSMutableArray<NSString *> *textLines = [NSMutableArray array];
        double confidenceTotal = 0.0;
        double confidenceMinimum = 1.0;
        for (VNRecognizedTextObservation *observation in observations) {
            VNRecognizedText *candidate = [observation topCandidates:1].firstObject;
            if (candidate == nil || candidate.string.length == 0) {
                continue;
            }
            CGRect box = observation.boundingBox;
            confidenceTotal += candidate.confidence;
            confidenceMinimum = MIN(confidenceMinimum, candidate.confidence);
            [textLines addObject:candidate.string];
            [lines addObject:@{
                @"text": candidate.string,
                @"confidence": @(candidate.confidence),
                @"bbox": @{
                    @"x": @(box.origin.x),
                    @"y": @(box.origin.y),
                    @"width": @(box.size.width),
                    @"height": @(box.size.height),
                },
            }];
        }

        NSString *fullText = [textLines componentsJoinedByString:@"\n"];
        NSUInteger wordCount = 0;
        for (NSString *part in [fullText componentsSeparatedByCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet]) {
            if (part.length > 0) {
                wordCount += 1;
            }
        }
        NSDictionary *payload = @{
            @"engine": @"apple_vision",
            @"mode": mode,
            @"languages": request.recognitionLanguages ?: @[],
            @"line_count": @(lines.count),
            @"char_count": @(fullText.length),
            @"word_count": @(wordCount),
            @"mean_confidence": lines.count > 0 ? @(confidenceTotal / lines.count) : @0,
            @"minimum_confidence": lines.count > 0 ? @(confidenceMinimum) : @0,
            @"text": fullText,
            @"lines": lines,
        };

        NSError *jsonError = nil;
        NSData *json = [NSJSONSerialization dataWithJSONObject:payload options:0 error:&jsonError];
        if (json == nil || jsonError != nil) {
            failWithMessage([NSString stringWithFormat:@"Cannot serialize OCR result: %@", jsonError]);
        }
        fwrite(json.bytes, 1, json.length, stdout);
        fputc('\n', stdout);
    }
    return 0;
}
