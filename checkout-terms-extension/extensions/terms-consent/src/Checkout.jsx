import { useState } from 'react';
import {
  reactExtension,
  BlockStack,
  Checkbox,
  Link,
  Text,
  useApplyAttributeChange,
  useAttributeValues,
  useBuyerJourneyIntercept,
  useSettings,
  useTranslate,
} from '@shopify/ui-extensions-react/checkout';

// שם ה-cart attribute – זהה לזה שהתבנית שומרת בעגלה, כך שההזמנה מקבלת
// את האישור בין אם הלקוח הגיע מהעגלה ובין אם ישירות לדף התשלום.
const ATTRIBUTE_KEY = 'אישור תקנון';
const ATTRIBUTE_VALUE = 'כן';
const DEFAULT_TERMS_URL = 'https://www.seora.co.il/policies/terms-of-service';
const DEFAULT_PRIVACY_URL = 'https://www.seora.co.il/policies/privacy-policy';

export default reactExtension('purchase.checkout.block.render', () => <TermsConsent />);

function TermsConsent() {
  const t = useTranslate();
  const settings = useSettings();
  const applyAttributeChange = useApplyAttributeChange();
  const [savedValue] = useAttributeValues([ATTRIBUTE_KEY]);

  const [checked, setChecked] = useState(savedValue === ATTRIBUTE_VALUE);
  const [error, setError] = useState(undefined);

  const labelPrefix = settings.label_prefix || t('label_prefix');
  const termsText = settings.terms_link_text || t('terms_link');
  const termsUrl = settings.terms_url || DEFAULT_TERMS_URL;
  const privacyText = settings.privacy_link_text ?? t('privacy_link');
  const privacyUrl = settings.privacy_url || DEFAULT_PRIVACY_URL;
  const errorText = settings.error_text || t('error');

  // חוסם את המעבר לשלב הבא / לחיצה על "שלם עכשיו" כל עוד התיבה לא מסומנת.
  useBuyerJourneyIntercept(({ canBlockProgress }) => {
    if (canBlockProgress && !checked) {
      return {
        behavior: 'block',
        reason: 'Terms of service not accepted',
        perform: () => setError(errorText),
      };
    }
    return {
      behavior: 'allow',
      perform: () => setError(undefined),
    };
  });

  async function onChange(value) {
    setChecked(value);
    if (value) setError(undefined);
    await applyAttributeChange({
      type: 'updateAttribute',
      key: ATTRIBUTE_KEY,
      value: value ? ATTRIBUTE_VALUE : '',
    });
  }

  return (
    <BlockStack spacing="tight">
      <Checkbox id="seora-terms" name="seora-terms" checked={checked} onChange={onChange} error={error}>
        <Text>
          {labelPrefix}{' '}
          <Link to={termsUrl} external>
            {termsText}
          </Link>
          {privacyText ? (
            <>
              {' '}
              {t('and')}{' '}
              <Link to={privacyUrl} external>
                {privacyText}
              </Link>
            </>
          ) : null}
        </Text>
      </Checkbox>
    </BlockStack>
  );
}
